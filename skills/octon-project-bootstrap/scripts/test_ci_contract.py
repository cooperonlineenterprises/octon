#!/usr/bin/env python3
"""In-memory adversarial checks for the source CI admission contract."""
from pathlib import Path
import unittest
import validate_octon_mini as V


class CIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow=(V.ROOT/'.github/workflows/validate.yml').read_text()

    def issues(self,value):
        issues=[];V.validate_ci_contract(issues,value);return issues

    def test_current_exact_five_job_contract(self):
        self.assertEqual(self.issues(self.workflow),[])

    def test_mutations_cannot_launder_skips_or_weaken_qualified_profile(self):
        cases=[
            ('needs: protected-linux-fixture','needs: missing-job'),
            ("if: always() && github.event_name == 'pull_request'","if: github.event_name == 'pull_request'"),
            ('run: test "$OCTON_PROTECTED_RESULT" = success','run: test "$OCTON_PROTECTED_RESULT" = skipped'),
            ('run: test "$OCTON_PROTECTED_RESULT" = success','run: test "$OCTON_PROTECTED_RESULT" = success || true'),
            ('OCTON_PROTECTED_RESULT: ${{ needs.protected-linux-fixture.result }}','OCTON_PROTECTED_RESULT: success'),
            ('name: required\n','name: required\n    continue-on-error: true\n'),
            ('name: protected Linux fixture\n','name: protected Linux fixture\n    continue-on-error: true\n'),
            ("if: github.event_name == 'pull_request' || github.event_name == 'workflow_dispatch'","if: github.event_name == 'workflow_dispatch'"),
            ('persist-credentials: false','persist-credentials: true'),
            ('--network none --cap-drop ALL','--network host --cap-drop ALL'),
            ('--security-opt no-new-privileges --read-only','--security-opt no-new-privileges --privileged'),
            ('--tmpfs /evidence:rw,nosuid,nodev,size=64m','-v /host/results:/evidence:rw'),
            ('--cap-add KILL \\\n','--cap-add KILL --pid=host \\\n'),
            ('--qualify-linux-container --output /evidence/qualification.json --emit-evidence','--output /evidence/qualification.json'),
            ('--output /evidence/qualification.json --emit-evidence','--output /evidence/qualification.json --emit-evidence || true'),
            ('--output /evidence/qualification.json --emit-evidence\n','--output /evidence/qualification.json --emit-evidence\n          true\n'),
            ('run: |\n          docker run','run: |\n          set +e\n          docker run'),
            ('fetch-depth: 0','fetch-depth: 1'),
            ('d23441a48e516b6c34aea4fa41551a30e30af803','0000000000000000000000000000000000000000'),
            ('os: [ubuntu-latest, macos-latest, windows-latest]','os: [ubuntu-latest]'),
            ('python: ["3.11", "3.12", "3.13", "3.14"]','python: ["3.14"]'),
            ("cancel-in-progress: ${{ github.event_name == 'pull_request' }}",'cancel-in-progress: true'),
            ('branches:\n      - main','branches:\n      - main\n      - qualification/**'),
        ]
        for before,after in cases:
            with self.subTest(mutation=before):
                self.assertIn(before,self.workflow)
                self.assertTrue(self.issues(self.workflow.replace(before,after,1)),before)


if __name__=='__main__':unittest.main(verbosity=2)
