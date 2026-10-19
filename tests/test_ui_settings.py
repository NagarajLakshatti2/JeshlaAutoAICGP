import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from agent.config.ui_settings import save_model_settings

class SettingsTests(unittest.TestCase):
    def test_preserves_keys_comments_multiline_and_other_providers(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict('os.environ',{},clear=True):
            path=Path(folder)/'.env'
            path.write_bytes(b'# keep\r\nGROQ_API_KEY="private-fixture"\r\nNOTE="multi\r\nLLM_PROVIDER=inside-note\r\nline"\r\nLLM_PROVIDER=ollama\r\nOLLAMA_MODEL=local-model\r\n')
            result=save_model_settings(path,'groq','openai/gpt-oss-20b')
            data=path.read_bytes()
            self.assertIn(b'GROQ_API_KEY="private-fixture"\r\n',data)
            self.assertIn(b'LLM_PROVIDER=inside-note\r\n',data)
            self.assertIn(b'LLM_PROVIDER=groq\r\n',data)
            self.assertIn(b'OLLAMA_MODEL=local-model\r\n',data)
            self.assertNotIn('private-fixture',json.dumps(result))
            self.assertEqual(list(Path(folder).glob('.model-settings-*')),[])

    def test_invalid_missing_key_and_invalid_file_do_not_write(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict('os.environ',{},clear=True):
            path=Path(folder)/'.env';path.write_text('LLM_PROVIDER=ollama\n',encoding='utf-8')
            original=path.read_bytes()
            for provider,model in [('groq','model'),('unknown','model'),('ollama','bad\nKEY=x')]:
                with self.assertRaises(ValueError):save_model_settings(path,provider,model)
                self.assertEqual(path.read_bytes(),original)
            path.write_text('BROKEN="unterminated\n',encoding='utf-8');original=path.read_bytes()
            with self.assertRaises(ValueError):save_model_settings(path,'ollama','valid')
            self.assertEqual(path.read_bytes(),original)

    def test_ollama_and_gemini_alias_supported(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict('os.environ',{},clear=True):
            path=Path(folder)/'.env'
            save_model_settings(path,'ollama','qwen:small')
            with path.open('a',encoding='utf-8') as handle:handle.write('GOOGLE_AI_STUDEO_KEY=fixture\n')
            self.assertTrue(save_model_settings(path,'gemini','fixture-model')['restart_required'])
