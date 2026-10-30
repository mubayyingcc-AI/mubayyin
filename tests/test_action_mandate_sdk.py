import unittest
from unittest.mock import patch
from sdk.python.mubayyin_client import MubayyinClient

class FakeResponse:
    def __init__(self, body=b'{"assessment_id":"ama_test"}'): self.body=body
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self): return self.body

class FakeOpener:
    def __init__(self): self.calls=[]
    def open(self,request,timeout):
        self.calls.append((request,timeout))
        return FakeResponse()

class ActionMandateSDKTests(unittest.TestCase):
    def setUp(self):
        self.client=MubayyinClient("https://example.test","k"*40)
        self.fake=FakeOpener()
        self.patch=patch("sdk.python.mubayyin_client._NO_REDIRECT_OPENER",self.fake)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_create_mandate_posts_to_tenant_endpoint(self):
        self.client.create_action_mandate(mandate_id="m-1")
        req,_=self.fake.calls[-1]
        self.assertEqual(req.full_url,"https://example.test/tenant/action-mandates")
        self.assertEqual(req.get_method(),"POST")

    def test_revoke_mandate_uses_encoded_path_segment(self):
        self.client.revoke_action_mandate("m-1")
        req,_=self.fake.calls[-1]
        self.assertEqual(req.full_url,"https://example.test/tenant/action-mandates/m-1/revoke")
        self.assertEqual(req.get_method(),"POST")

    def test_assess_action_posts_proposal(self):
        result=self.client.assess_action(mandate_id="m-1",request_id="r-1")
        req,_=self.fake.calls[-1]
        self.assertEqual(result,{"assessment_id":"ama_test"})
        self.assertEqual(req.full_url,"https://example.test/tenant/action-assessments")

    def test_get_action_assessment_reads_tenant_evidence(self):
        self.client.get_action_assessment("ama_test")
        req,_=self.fake.calls[-1]
        self.assertEqual(req.full_url,"https://example.test/tenant/action-assessments/ama_test")
        self.assertEqual(req.get_method(),"GET")

if __name__ == "__main__":
    unittest.main()
