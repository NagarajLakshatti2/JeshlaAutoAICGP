"""CI bundles are scoped review artifacts, never publication or release proof."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.tools.project_tools import ProjectTools
from integrations.ci.gradle import prepare_ci_bundle


class CiBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"target";self.root.mkdir()
        self.boundary=Path(self.tmp.name)/"agent"
        self.patcher=patch("integrations.ci.gradle.ROOT",self.boundary);self.patcher.start();self.addCleanup(self.patcher.stop)
        self.api=["API_TC_001_directLookupMatchesRequestedUser","API_TC_002_existingFilterMatchesDirectLookup","API_TC_003_absentIdFilterReturnsEmptyCollection"]
        self.web=["TI_TC_001_textEntryAndClear"]
        files={"build.gradle":"plugins { id 'java' }\nplaywrightVersion='fixture'\ntestngVersion='fixture'\nrestassuredVersion='fixture'\njacksonVersion='fixture'\n",
               "src/main/java/config/ConfigReader.java":"package config; class ConfigReader {}\n",
               "src/test/java/tests/api/Pilot.java":"package tests.api; class Pilot {"+"".join("void "+m+"() {}" for m in self.api)+"}\n",
               "src/test/java/tests/web/Pilot.java":"package tests.web; class Pilot { void TI_TC_001_textEntryAndClear() {} }\n",
               "gradlew":"#!/bin/sh\nexit 99 # must never run during preparation\n"}
        for name,text in files.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding="utf-8")
        names=set(files)-{"gradlew"}
        self.profile={"version":1,"api":{"class":"tests.api.Pilot","methods":self.api,"url":"https://example.com","user_id":1},
                      "web":{"class":"tests.web.Pilot","methods":self.web,"url":"https://example.org/#inputs","by":"label","target":"Reviewed field","value":"Hello World","dismiss":"Decline"},
                      "source_text_sha256":{name:self.digest(name) for name in names}}
        self.out=self.boundary/"outputs/acceptance/one"

    def digest(self,name):
        return hashlib.sha256((self.root/name).read_text(encoding="utf-8-sig").encode("utf-8")).hexdigest()

    def prepare(self):
        return prepare_ci_bundle(ProjectTools(self.root),self.out,self.profile)

    def test_preparation_only_creates_three_review_files_not_target_changes(self):
        before={p:p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with patch("subprocess.run",side_effect=AssertionError("must not execute")),patch("requests.sessions.Session.request",side_effect=AssertionError("no network")):
            result=self.prepare()
        self.assertEqual(len(result["files"]),3)
        self.assertEqual(result["status"],"P")
        self.assertFalse(result["publication_or_dispatch_performed"])
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_source_hash_change_requires_review_before_any_artifact_write(self):
        (self.root/"src/test/java/tests/api/Pilot.java").write_text("changed",encoding="utf-8")
        with self.assertRaises(ValueError):self.prepare()
        self.assertFalse(self.out.exists())

    def test_line_ending_only_changes_preserve_source_text_digest(self):
        path=self.root/"src/test/java/tests/api/Pilot.java"
        text=path.read_text(encoding="utf-8").replace("\r\n","\n")
        path.write_bytes(b"\xef\xbb\xbf"+text.replace("\n","\r\n").encode("utf-8"))
        self.assertEqual(self.digest("src/test/java/tests/api/Pilot.java"),self.profile["source_text_sha256"]["src/test/java/tests/api/Pilot.java"])
        self.assertEqual(self.prepare()["status"],"P")

    def test_invalid_cases_origins_and_scope_are_rejected_before_write(self):
        original=copy.deepcopy(self.profile)
        variations=[("api","methods",self.api+self.api[:1]),("api","methods",["inventedMethod"]),
                    ("api","url","http://example.com"),("api","url","https://127.0.0.1"),("web","url","https://localhost"),("api","url","https://user:secret@example.com"),
                    ("web","url","https://example.org/?token=secret"),("web","by","css"),
                    ("web","dismiss","Accept"),("api","user_id",True)]
        for lane,key,value in variations:
            self.profile=copy.deepcopy(original);self.profile[lane][key]=value
            with self.subTest(lane=lane,key=key),self.assertRaises(ValueError):self.prepare()
        self.assertFalse(self.out.exists())

    def test_unknown_fields_or_unbound_extra_source_are_not_allowed(self):
        self.profile["run_now"]=True
        with self.assertRaises(ValueError):self.prepare()
        del self.profile["run_now"]
        self.profile["source_text_sha256"]["../outside.java"]="0"*64
        with self.assertRaises(ValueError):self.prepare()

    def test_cannot_overwrite_review_bundle_or_write_outside_acceptance(self):
        self.prepare()
        with self.assertRaises(FileExistsError):self.prepare()
        with self.assertRaises(ValueError):prepare_ci_bundle(ProjectTools(self.root),self.root/"ci",self.profile)

    def test_selected_methods_must_exist_in_inspected_source(self):
        path=self.root/"src/test/java/tests/web/Pilot.java";path.write_text("class Pilot {}",encoding="utf-8")
        self.profile["source_text_sha256"]["src/test/java/tests/web/Pilot.java"]=self.digest("src/test/java/tests/web/Pilot.java")
        with self.assertRaisesRegex(ValueError,"method is absent"):self.prepare()

    def test_templates_are_explicitly_packaged_for_installed_usage(self):
        import tomllib
        root=Path(__file__).resolve().parents[1]
        settings=tomllib.loads((root/"pyproject.toml").read_text(encoding="utf-8"))
        patterns=settings["tool"]["setuptools"]["package-data"]["integrations.ci"]
        self.assertIn("templates/*.gradle",patterns);self.assertIn("templates/*.yml",patterns)
        self.prepare()
        workflow=(self.out/".github/workflows/ws9-selected-pilots.yml").read_text()
        self.assertIn("workflow_dispatch:",workflow)
        self.assertNotIn("pull_request:",workflow);self.assertNotIn("  push:",workflow)
        self.assertNotIn("secrets.",workflow)
        self.assertIn("contents: read",workflow)
        self.assertIn("persist-credentials: false",workflow)
        self.assertIn("if: always()",workflow)


if __name__=="__main__":unittest.main()
