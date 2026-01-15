import pytest


def test_create_bin_under_parent(test_controller):
    db = test_controller.db_manager
    root_id = db.ensure_root_exists()

    parent_id = db.create_bin("TestProjects", root_id)
    child_id = db.create_bin("TestInbox", parent_id)

    parent = db.get_parent_bin(child_id)
    assert parent and parent["id"] == parent_id
    assert db.get_bin_name(child_id) == "TestInbox"

    # Duplicates (case-insensitive) are rejected.
    with pytest.raises(ValueError):
        db.create_bin("testinbox", parent_id)


def test_rename_bin_rejects_system_bins(test_controller):
    db = test_controller.db_manager
    root_id = db.ensure_root_exists()
    bin_id = db.create_bin("TestIdeas", root_id)

    db.rename_bin(bin_id, "Archive")
    assert db.get_bin_name(bin_id) == "Archive"

    # System bins can’t be renamed.
    with pytest.raises(ValueError):
        db.rename_bin(root_id, "Nope")


def test_move_bin_to_parent_updates_links_and_checks_cycles(test_controller):
    db = test_controller.db_manager
    root_id = db.ensure_root_exists()
    parent_id = db.create_bin("TestClients", root_id)
    child_id = db.create_bin("TestAcme", parent_id)

    # Moving under itself is forbidden.
    with pytest.raises(ValueError):
        db.move_bin_to_parent(child_id, child_id)

    # Moving a bin under its descendant raises.
    with pytest.raises(ValueError):
        db.move_bin_to_parent(parent_id, child_id)

    # Moving a child to root updates its parent link.
    db.move_bin_to_parent(child_id, root_id)
    assert db.get_parent_bin(child_id)["id"] == root_id


def test_mark_bin_deleted_moves_bin(test_controller):
    db = test_controller.db_manager
    root_id = db.ensure_root_exists()
    bin_id = db.create_bin("ArchiveTest", root_id)
    unlinked_id = db.get_bin_id_by_name("unlinked")

    assert unlinked_id is not None

    db.mark_bin_deleted(bin_id)
    parent = db.get_parent_bin(bin_id)
    assert parent and parent["id"] == unlinked_id

    with pytest.raises(ValueError):
        db.mark_bin_deleted(root_id)
