import importlib.util,sys,os,shutil
from pathlib import Path
r=Path(r'D:\JeshlaAutoAI\outputs\workstream-5-completion-qa')
spec=importlib.util.spec_from_file_location('renderer',r'C:\Users\nagar\.codex\plugins\cache\openai-primary-runtime\documents\26.1015.12040\skills\documents\render_docx.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def convert(doc_path,user_profile,convert_tmp_dir,stem,verbose):
 p=Path(convert_tmp_dir)/(stem+'.pdf');shutil.copy2(r/'updated.pdf',p);return str(p),'Native Word export'
m.convert_to_pdf=convert
os.environ['PATH']=r'C:\Users\nagar\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin'+os.pathsep+os.environ['PATH']
sys.argv=['render_docx.py',str(r/'updated.docx'),'--output_dir',str(r/'pages-final'),'--dpi','95']
m.main()

