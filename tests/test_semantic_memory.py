import unittest
from agent.memory.long_term_memory import LongTermMemory
from agent.memory.semantic_search import rank_facts
class Encoder:
    def encode(self,texts,**kwargs):return [[1.,0.]]+[[1.,0.] if "train" in text else [0.,1.] for text in texts[1:]]
class SemanticMemoryTests(unittest.TestCase):
    def test_paraphrase_rank_scope_and_current_values(self):
        with LongTermMemory(":memory:") as m:
            m.save("u","p","travel","I commute by train")
            m.save("u","p","other","I like apples")
            m.save("other","p","private","train secret")
            result=m.semantic_search("u","p","How do I get to work?",encoder=Encoder())
            self.assertEqual([r["key"] for r in result["facts"]],["travel"])
            m.save("u","p","travel","I commute by bicycle")
            self.assertEqual(m.semantic_search("u","p","commuting",encoder=Encoder())["facts"],[])
            m.delete("u","p","travel")
            self.assertEqual(m.semantic_search("u","p","commuting",encoder=Encoder())["facts"],[])
    def test_empty_scope_does_not_load_model(self):
        with LongTermMemory(":memory:") as m:
            self.assertEqual(m.semantic_search("u","p","test")["facts"],[])
    def test_scope_coverage_is_reported(self):
        with LongTermMemory(":memory:") as m:
            for i in range(201):m.save("u","p",str(i),"train")
            r=m.semantic_search("u","p","commute",limit=3,encoder=Encoder())
            self.assertTrue(r["truncated"]);self.assertEqual(len(r["facts"]),3)
    def test_invalid_vectors_rejected(self):
        class Bad:
            def encode(self,*args,**kwargs):return [[1.],[float("nan")]]
        with self.assertRaises(ValueError):rank_facts([{"key":"x","value":"x"}],"query",1,encoder=Bad())
