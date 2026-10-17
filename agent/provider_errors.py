"""Safe provider diagnostics and bounded retries; never logs provider bodies or secrets."""
import os
import time
import requests


class ProviderError(RuntimeError):
    def __init__(self, provider, category, explanation, *, status=None, retryable=False, attempts=1):
        self.provider=provider
        self.category=category
        self.status=status
        self.retryable=retryable
        self.attempts=attempts
        http=f" | HTTP {status}" if status is not None else ""
        super().__init__(f"{provider.upper()} [{category}]{http} | {explanation} | Attempts: {attempts}. No action was executed from this failed response.")


def response_error(provider, response, attempt=1):
    status=response.status_code
    try:
        data=response.json()
        error=data.get("error",{}) if isinstance(data,dict) else {}
        code=str(error.get("code", "")) if isinstance(error,dict) else ""
        detail=str(error.get("message", "")).casefold() if isinstance(error,dict) else ""
    except (ValueError,TypeError,AttributeError):
        code=detail=""
    # Inspect for known categories, but never echo untrusted error text/failed generations.
    category="HTTP_ERROR"; message="Provider rejected the request. Check its service status and configuration."; retry=False
    if status==401:
        category="AUTHENTICATION";message="API key is missing, invalid or revoked. Check the local key; do not paste it into chat."
    elif status==403:
        category="ACCESS_DENIED";message="Account, model or policy access was denied. Check provider permissions."
    elif status==402:
        category="BILLING";message="Credits or billing access are insufficient. Check the account dashboard."
    elif status==404 or code in {"model_not_found","model_decommissioned"}:
        category="MODEL_OR_ENDPOINT";message="Model or endpoint was not found. Check the selected model ID and availability."
    elif code in {"context_length_exceeded","context_window_exceeded"} or (status==400 and any(s in detail for s in ("context length","context window","too many tokens"))):
        category="CONTEXT_LIMIT";message="Input exceeds the model context budget. Narrow the request or reduce retained evidence."
    elif code in {"tool_use_failed","json_validate_failed"}:
        category="TOOL_OUTPUT";message="Provider rejected generated tool/JSON output. Check tool registration/schema or narrow the request."
    elif status in {400,422}:
        category="INVALID_REQUEST";message="Request parameters, schema or model capabilities are incompatible. Check request settings; unchanged retries will not fix this."
    elif status==413:
        category="REQUEST_TOO_LARGE";message="Request body is too large. Reduce document/evidence size."
    elif status==429:
        if code in {"insufficient_quota","quota_exceeded","daily_limit_exceeded"} or any(s in detail for s in ("daily limit","per day","per-day","billing","insufficient quota","free-models-per-day")):
            category="QUOTA_EXHAUSTED";message="Account quota appears exhausted. Check the dashboard/reset time; no automatic retry."
        else:
            category="RATE_LIMIT";message="Provider rate or quota limit reached. Check account limits; only a short explicit Retry-After permits an automatic retry.";retry=True
    elif status in {408,500,502,503,504}:
        category="PROVIDER_TEMPORARY";message="Provider or gateway is temporarily unavailable.";retry=True
    elif 300<=status<400:
        category="REDIRECT_BLOCKED";message="Unexpected redirect was blocked to avoid forwarding credentials. Check endpoint/proxy configuration."
    return ProviderError(provider,category,message,status=status,retryable=retry,attempts=attempt)


def request_model(provider,url,*,headers,json,timeout,allow_redirects=False):
    prefix=provider.upper()
    def setting(suffix,default,minimum,maximum):
        try:
            value=int(os.getenv(prefix+suffix,str(default)))
            if not minimum<=value<=maximum: raise ValueError()
            return value
        except (TypeError,ValueError):
            raise ProviderError(provider,"CONFIGURATION",f"{prefix+suffix} must be an integer from {minimum} to {maximum}.",attempts=0) from None
    connect=setting("_CONNECT_TIMEOUT",30,5,120)
    attempts=setting("_CONNECT_ATTEMPTS",2,1,3)
    for attempt in range(1,attempts+1):
        try:
            response=requests.post(url,headers=headers,json=json,timeout=(connect,timeout[1]),allow_redirects=allow_redirects)
        except requests.exceptions.SSLError:
            raise ProviderError(provider,"TLS_CERTIFICATE","Check system time, trusted certificates or proxy settings; no retry performed.",attempts=attempt) from None
        except requests.exceptions.ProxyError:
            raise ProviderError(provider,"PROXY","Proxy connection failed. Check proxy settings/credentials; no retry performed.",attempts=attempt) from None
        except requests.exceptions.ReadTimeout:
            raise ProviderError(provider,"RESPONSE_TIMEOUT","Model response timed out after connection. No automatic retry; retry manually when connectivity improves.",attempts=attempt) from None
        except (requests.exceptions.ConnectTimeout,requests.exceptions.ConnectionError) as error:
            category="CONNECT_TIMEOUT" if isinstance(error,requests.exceptions.ConnectTimeout) else "CONNECTION"
            if attempt==attempts:
                raise ProviderError(provider,category,f"Model connection failed after {attempts} attempt(s). Check internet, DNS, proxy or local server availability.",retryable=True,attempts=attempt) from None
            print(f"{prefix} [{category}]: retrying model request ({attempt+1}/{attempts}); no action executed from this response.")
            time.sleep(1)
            continue
        except requests.RequestException:
            raise ProviderError(provider,"TRANSPORT","Request transport failed; no automatic retry.",attempts=attempt) from None
        if response.status_code<300: return response
        error=response_error(provider,response,attempt)
        delay=1
        if response.status_code==429:
            try: delay=float(getattr(response,"headers",{}).get("Retry-After","nan"))
            except (TypeError,ValueError): delay=float("nan")
            if not 0<=delay<=5: raise error
        if not error.retryable or attempt==attempts: raise error
        print(f"{prefix} [{error.category}] HTTP {response.status_code}: retrying model request ({attempt+1}/{attempts}) in {delay:g}s.")
        time.sleep(delay)
    raise ProviderError(provider,"TRANSPORT","Request did not complete.")


def read_model_json(response, provider):
    try:
        data=response.json()
        if not isinstance(data,dict): raise ValueError()
    except (ValueError,TypeError):
        raise ProviderError(provider,"INVALID_RESPONSE","Provider returned malformed JSON or an unexpected response shape; no automatic retry.") from None
    if data.get("error"):
        raise ProviderError(provider,"MODEL_ERROR","Provider returned an error inside a successful HTTP response. Check model/service availability; no automatic retry.")
    return data
