```
dag ~/Projects/tklr-uv % tar -tzf dist/*.tar.gz | sed -n '1,120p'
tklr_dgraham-0.0.0rc1/
tklr_dgraham-0.0.0rc1/PKG-INFO
tklr_dgraham-0.0.0rc1/README.md
tklr_dgraham-0.0.0rc1/pyproject.toml
tklr_dgraham-0.0.0rc1/setup.cfg
tklr_dgraham-0.0.0rc1/src/
tklr_dgraham-0.0.0rc1/src/tklr/
tklr_dgraham-0.0.0rc1/src/tklr/__init__.py
tklr_dgraham-0.0.0rc1/src/tklr/cli/
tklr_dgraham-0.0.0rc1/src/tklr/cli/main.py
tklr_dgraham-0.0.0rc1/src/tklr/cli/migrate_etm_to_tklr.py
tklr_dgraham-0.0.0rc1/src/tklr/common.py
tklr_dgraham-0.0.0rc1/src/tklr/controller.py
tklr_dgraham-0.0.0rc1/src/tklr/item.py
tklr_dgraham-0.0.0rc1/src/tklr/list_colors.py
tklr_dgraham-0.0.0rc1/src/tklr/model.py
tklr_dgraham-0.0.0rc1/src/tklr/shared.py
tklr_dgraham-0.0.0rc1/src/tklr/tklr_env.py
tklr_dgraham-0.0.0rc1/src/tklr/versioning.py
tklr_dgraham-0.0.0rc1/src/tklr/view.py
tklr_dgraham-0.0.0rc1/src/tklr/view_agenda.py
tklr_dgraham-0.0.0rc1/src/tklr_dgraham.egg-info/
tklr_dgraham-0.0.0rc1/src/tklr_dgraham.egg-info/PKG-INFO
tklr_dgraham-0.0.0rc1/src/tklr_dgraham.egg-info/SOURCES.txt
tklr_dgraham-0.0.0rc1/src/tklr_dgraham.egg-info/dependency_links.txt
tklr_dgraham-0.0.0rc1/src/tklr_dgraham.egg-info/entry_points.txt
tklr_dgraham-0.0.0rc1/src/tklr_dgraham.egg-info/requires.txt
tklr_dgraham-0.0.0rc1/src/tklr_dgraham.egg-info/top_level.txt
```

```
dag ~/Projects/tklr-uv % Tree src/tklr
src/tklr
├── __init__.py
├── cli
│   ├── main.py
│   └── migrate_etm_to_tklr.py
├── common.py
├── controller.py
├── item.py
├── list_colors.py
├── model.py
├── shared.py
├── tklr_env.py
├── versioning.py
├── view_agenda.py
├── view_textual.css
└── view.py
```

Why is view_textual.css omitted from the build?
