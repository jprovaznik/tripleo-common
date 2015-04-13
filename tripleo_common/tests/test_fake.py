from tripleo_common.tests import base


# jprovazn: there is a check that at least one test should run,
# this fake test will be removed with a first real test added.
class FakeTest(base.TestCase):

    def test_fake(self):
        pass
