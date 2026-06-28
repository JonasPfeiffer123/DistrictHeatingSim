"""Unit tests for the GUI-free project-structure helpers.

``discover_variants`` was extracted from three near-identical (and subtly
divergent) inline scans in the GUI (main_view / main_presenter / comparison_tab)
as the first slice of the main_view god-object decomposition (BACKLOG B1). These
tests are the seam that the GUI versions never had.
"""

import os

import pytest

from districtheatingsim.gui.MainTab.project_structure import (
    DEFAULT_VARIANT_NAME,
    PROJECT_INPUT_FOLDERS,
    VARIANT_PREFIX,
    VARIANT_SUBDIRS,
    create_project_structure,
    create_variant_structure,
    discover_variants,
    resolve_new_project_start_dir,
)


def test_default_variant_name_matches_prefix():
    assert VARIANT_PREFIX == "Variante"
    assert DEFAULT_VARIANT_NAME == "Variante 1"
    assert DEFAULT_VARIANT_NAME.startswith(VARIANT_PREFIX)


def test_missing_path_returns_empty(tmp_path):
    assert discover_variants(str(tmp_path / "does_not_exist")) == []


def test_path_is_a_file_returns_empty(tmp_path):
    f = tmp_path / "a_file.txt"
    f.write_text("x", encoding="utf-8")
    assert discover_variants(str(f)) == []


def test_empty_project_returns_empty(tmp_path):
    assert discover_variants(str(tmp_path)) == []


def test_discovers_only_variant_directories(tmp_path):
    (tmp_path / "Variante 1").mkdir()
    (tmp_path / "Variante 2").mkdir()
    (tmp_path / "Eingangsdaten allgemein").mkdir()  # non-variant folder
    (tmp_path / "Definition Quartier IST").mkdir()
    assert discover_variants(str(tmp_path)) == ["Variante 1", "Variante 2"]


def test_files_named_like_a_variant_are_excluded(tmp_path):
    (tmp_path / "Variante 1").mkdir()
    (tmp_path / "Variante 9.txt").write_text("not a folder", encoding="utf-8")
    assert discover_variants(str(tmp_path)) == ["Variante 1"]


def test_result_is_sorted_deterministically(tmp_path):
    # Created out of order; discovery must return them sorted so "activate the
    # first variant" is deterministic regardless of filesystem order.
    for name in ("Variante 3", "Variante 1", "Variante 2"):
        (tmp_path / name).mkdir()
    assert discover_variants(str(tmp_path)) == ["Variante 1", "Variante 2", "Variante 3"]


def test_create_variant_structure_makes_all_subdirs(tmp_path):
    variant = tmp_path / "Variante 1"
    create_variant_structure(str(variant))
    for sub in VARIANT_SUBDIRS:
        assert (variant / sub).is_dir()


def test_create_variant_structure_is_idempotent(tmp_path):
    variant = tmp_path / "Variante 1"
    create_variant_structure(str(variant))
    create_variant_structure(str(variant))  # must not raise on existing dirs
    assert (variant / VARIANT_SUBDIRS[0]).is_dir()


def test_create_project_structure_full_layout(tmp_path):
    project = tmp_path / "Neues Projekt"
    create_project_structure(str(project))
    for folder in PROJECT_INPUT_FOLDERS:
        assert (project / folder).is_dir()
    # Default variant present with all its sub-folders, discoverable.
    assert discover_variants(str(project)) == [DEFAULT_VARIANT_NAME]
    for sub in VARIANT_SUBDIRS:
        assert (project / DEFAULT_VARIANT_NAME / sub).is_dir()


def test_create_project_structure_refuses_existing_project(tmp_path):
    project = tmp_path / "Neues Projekt"
    project.mkdir()
    with pytest.raises(FileExistsError):
        create_project_structure(str(project))


# ----------------------------------------------------------------------------
# resolve_new_project_start_dir — start directory for the new-project picker
# (extracted from main_view.on_create_new_project; BACKLOG B1)
# ----------------------------------------------------------------------------


def test_start_dir_prefers_parent_of_most_recent_project(tmp_path):
    recent = [str(tmp_path / "Projekte" / "Projekt A"), str(tmp_path / "Old" / "Projekt B")]
    assert resolve_new_project_start_dir(recent) == str(tmp_path / "Projekte")


def test_start_dir_falls_back_to_documents_when_no_recent(monkeypatch, tmp_path):
    # No recent projects -> ~/Documents if it exists.
    home = tmp_path / "home"
    (home / "Documents").mkdir(parents=True)
    monkeypatch.setattr(os.path, "expanduser", lambda p: p.replace("~", str(home)))
    assert os.path.normpath(resolve_new_project_start_dir([])) == os.path.normpath(str(home / "Documents"))


def test_start_dir_falls_back_to_home_when_no_documents(monkeypatch, tmp_path):
    # No recent projects and no ~/Documents -> home directory.
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda p: p.replace("~", str(home)))
    assert resolve_new_project_start_dir([]) == str(home)


def test_start_dir_recent_without_parent_falls_back(monkeypatch, tmp_path):
    # A bare recent entry (no directory component) must not be returned as start dir.
    home = tmp_path / "home"
    (home / "Documents").mkdir(parents=True)
    monkeypatch.setattr(os.path, "expanduser", lambda p: p.replace("~", str(home)))
    assert os.path.normpath(resolve_new_project_start_dir(["Projekt"])) == os.path.normpath(str(home / "Documents"))
