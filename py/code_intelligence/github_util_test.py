"""Unittest for github_util. """
import logging
import pytest

from code_intelligence import github_util

def test_build_issue_doc():
  result = github_util.build_issue_doc("someOrg", "someRepo", "issue title",
                                       ["line1", "line2"])

  expected = """issue title
someorg_somerepo
line1
line2"""
  assert result == expected

if __name__ == "__main__":
  logging.basicConfig(
      level=logging.INFO,
      format=('%(levelname)s|%(asctime)s'
              '|%(pathname)s|%(lineno)d| %(message)s'),
      datefmt='%Y-%m-%dT%H:%M:%S',
  )
  logging.getLogger().setLevel(logging.INFO)

  pytest.main()



