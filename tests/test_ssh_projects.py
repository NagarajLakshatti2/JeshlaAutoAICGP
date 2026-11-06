import unittest
from unittest.mock import patch
from types import SimpleNamespace
from integrations.git.repositories import repository_url, git_command
from agent.storage.projects import ProjectConfigurationError


class SSHProjectTests(unittest.TestCase):
    def test_supported_ssh_identity_and_rejections(self):
        self.assertEqual(repository_url("git@github.com:owner/repo.git"),
                         "ssh://git@github.com/owner/repo.git")
        self.assertEqual(repository_url("ssh://git@gitlab.com/group/sub/repo"),
                         "ssh://git@gitlab.com/group/sub/repo.git")
        for url in ("ssh://root@github.com/a/b", "ssh://git@localhost/a/b",
                    "ssh://git@github.com:22/a/b", "git@github.com:a/../b",
                    "ssh://git@github.com/a/b?command=x"):
            with self.subTest(url=url), self.assertRaises(ProjectConfigurationError):
                repository_url(url)

    def test_transport_enforces_noninteractive_verified_ssh(self):
        with patch("integrations.git.repositories.shutil.which", return_value="git"), patch(
                "integrations.git.repositories.subprocess.run",
                return_value=SimpleNamespace(returncode=0, stdout="ok", stderr="")) as run:
            git_command(["ls-remote", "ssh://git@github.com/owner/repo.git"])
        command = run.call_args.kwargs["env"]["GIT_SSH_COMMAND"]
        self.assertIn("StrictHostKeyChecking=yes", command)
        self.assertIn("BatchMode=yes", command)
        self.assertIn("-F none", command)
