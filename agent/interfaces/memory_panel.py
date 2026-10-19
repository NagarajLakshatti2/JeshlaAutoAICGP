"""Readable, responsive display of scoped saved facts; no writes or model calls."""
import hashlib,json,re
import streamlit as st


def fact_rows(data):
    if isinstance(data,list):return [row for row in data if isinstance(row,dict) and 'key' in row and 'value' in row]
    rows=[]
    for line in str(data or '').splitlines():
        match=re.match(r'^- ([A-Za-z0-9_.-]+): (.*)$',line)
        if not match:continue
        try:
            value,end=json.JSONDecoder().raw_decode(match.group(2))
            rest=match.group(2)[end:]
            metadata=json.loads(rest.split('| metadata:',1)[1]) if '| metadata:' in rest else {}
            rows.append({'key':match.group(1),'value':value,**(metadata if isinstance(metadata,dict) else {})})
        except (ValueError,TypeError):continue
    return rows


def render_memory(data):
    rows=fact_rows(data)
    if not rows:
        if data:st.text_area('Saved memory',str(data),disabled=True,height=100,key='memory_fallback_'+hashlib.sha256(str(data).encode('utf-8')).hexdigest()[:20])
        else:st.caption('No saved facts yet.')
        return
    st.caption(str(len(rows))+' saved facts'+(' · showing first 50' if len(rows)>50 else ''))
    for row in rows[:50]:
        identity=hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False,default=str).encode('utf-8')).hexdigest()[:20]
        value=row['value'] if isinstance(row['value'],str) else json.dumps(row['value'],ensure_ascii=False)
        st.text_area(str(row['key']),value,disabled=True,height=80,key='memory_value_'+identity,width='stretch')
        with st.popover('Details',icon=':material/info:'):
            st.caption('Stored source: '+str(row.get('source_kind','unknown')))
            st.caption('Verification: '+str(row.get('verification_status','unverified')))
            st.caption('Created: '+str(row.get('created_at','unknown')))
            st.caption('Updated: '+str(row.get('updated_at','unknown')))
            if row.get('source_ref'):st.text_area('Source reference',str(row['source_ref']),disabled=True,height=80,key='memory_source_'+identity,width='stretch')
