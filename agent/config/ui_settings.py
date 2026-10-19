"""Allowlisted provider/model .env edits; never edit or return API key values."""
import codecs,os,re,tempfile,threading
from pathlib import Path
from dotenv import dotenv_values

_LOCK=threading.Lock()
PROVIDERS=("ollama","openrouter","groq","gemini")


def save_model_settings(path,provider,model):
    if provider not in PROVIDERS:raise ValueError("Choose a supported provider.")
    if not isinstance(model,str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./:@+\-]{0,199}",model):
        raise ValueError("Enter a model ID of 1–200 letters, numbers or model-path punctuation; spaces/newlines are not allowed.")
    path=Path(path)
    if path.is_symlink():raise ValueError("Settings file must not be a symbolic link.")
    with _LOCK:
        original=path.read_bytes() if path.exists() else b""
        if len(original)>1_000_000:raise ValueError("Settings file is too large to edit safely.")
        try:text=original.decode("utf-8-sig")
        except UnicodeDecodeError:raise ValueError("Settings file must use UTF-8.") from None
        values=dotenv_values(stream=__import__('io').StringIO(text))
        if provider!="ollama":
            from agent.providers.gemini import KEY_NAMES
            names=KEY_NAMES if provider=="gemini" else (provider.upper()+"_API_KEY",)
            if not any((os.getenv(name) or values.get(name) or "").strip() for name in names):
                raise ValueError("Configure this provider's API key locally before selecting it. Keys cannot be entered here.")
        if provider!="ollama":
            budget_key=provider.upper()+"_BUDGET_MODEL"
            bound=os.environ.get(budget_key,values.get(budget_key) or "").strip()
            if bound and bound!=model:
                raise ValueError("This model conflicts with the provider's model-specific budget. Update "+budget_key+" and its context/output limits locally before saving this model. Settings were not changed.")
        changes={"LLM_PROVIDER":provider,provider.upper()+"_MODEL":model}
        newline="\r\n" if "\r\n" in text else "\n"
        from dotenv.parser import parse_stream
        bindings=list(parse_stream(__import__("io").StringIO(text)))
        if any(binding.error for binding in bindings):raise ValueError("Settings contain invalid syntax. Correct .env locally before editing here.")
        found=set();updated=[]
        for binding in bindings:
            key=binding.key
            if key in changes:
                updated.append(key+"="+changes[key]+newline);found.add(key)
            else:updated.append(binding.original.string)
        if updated and not updated[-1].endswith(('\n','\r')):updated[-1]+=newline
        updated.extend(key+"="+value+newline for key,value in changes.items() if key not in found)
        encoded=(''.join(updated)).encode('utf-8')
        if original.startswith(codecs.BOM_UTF8):encoded=codecs.BOM_UTF8+encoded
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.model-settings-',delete=False) as handle:
                temporary=Path(handle.name);handle.write(encoded);handle.flush();os.fsync(handle.fileno())
            if path.exists():os.chmod(temporary,path.stat().st_mode)
            current=path.read_bytes() if path.exists() else b""
            if current!=original:raise ValueError("Settings changed during editing. Reload and try again.")
            os.replace(temporary,path);temporary=None
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)
    return {"provider":provider,"model":model,"restart_required":True}
