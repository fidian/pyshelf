from tests.unit_test_base import UnitTestBase
import tests.metadata_utils as utils
from tests.search.search_test_wrapper import SearchTestWrapper
from pyshelf.search.update_manager import UpdateManager
from pyshelf.search.metadata import Metadata


class UpdateManagerTest(UnitTestBase):
    def setUp(self):
        self.test_wrapper = SearchTestWrapper()
        self.update_manager = UpdateManager(self.test_wrapper.search_container)
        Metadata.init()

    def tearDown(self):
        meta = self.update_manager.get_metadata("test_key")
        meta.delete()

    def test_metadata_update(self):
        self.maxDiff = None
        self.update_manager.update("test_key", utils.get_meta())
        metadata = self.update_manager.get_metadata("test_key")
        self.assertEqual(metadata.to_dict(), utils.get_meta_elastic())

    def test_metadata_update_item(self):
        self.update_manager.update_item("test_key", utils.get_meta_item())
        metadata = self.update_manager.get_metadata("test_key").to_dict()
        got_it = False
        for item in metadata["items"]:
            if item["name"] == "tag2":
                self.assertEqual(item, utils.get_meta_item())
                got_it = True
        self.assertTrue(got_it)
