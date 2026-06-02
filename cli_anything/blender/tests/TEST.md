# Blender CLI Harness - Test Documentation

## Test Inventory

| File | Test Classes | Test Count | Focus |
|------|-------------|------------|-------|
| `test_core.py` | 6 | ~60 | Unit tests for scene, objects, materials, modifiers, lights/cameras, session |
| `test_full_e2e.py` | 4 | ~20 | E2E workflows with real Blender rendering |
| **Total** | **10** | **~80** | |

## Unit Tests (`test_core.py`)

All unit tests use synthetic/in-memory data only. No external files or Blender required.

### TestScene (10 tests)
- Create scene with defaults, custom dimensions, and named profiles
- Reject invalid render engines and negative/zero dimensions
- Save to JSON and re-open roundtrip
- Open nonexistent file raises error
- Get scene info and list available profiles
- Frame range validation

### TestObjects (15 tests)
- Add single and multiple objects; add with various mesh types
- Reject invalid mesh types and parameters
- Remove object by index; reject invalid index
- Duplicate object
- Transform object (translate, rotate, scale)
- Set object properties (name, visible, location, rotation, scale)
- Get object and list all objects
- Verify object IDs are unique across additions

### TestMaterials (10 tests)
- Create material with defaults and custom properties
- Reject invalid color format
- Assign material to object
- Set material properties (color, metallic, roughness, specular)
- List and get materials

### TestModifiers (10 tests)
- List available modifiers
- Get modifier info
- Add modifier to object
- Remove modifier by index
- Set modifier parameters
- List modifiers on object

### TestLightsAndCameras (8 tests)
- Add light with various types (point, sun, spot, area)
- Add camera
- Set light properties
- Set camera properties
- List lights and cameras

### TestSession (10 tests)
- Create session; set and get project
- Undo/redo cycle preserves state
- Undo on empty stack is no-op; redo on empty stack is no-op
- New snapshot clears redo stack
- Session status reports undo/redo depth
- Save session to file
- List history entries

## End-to-End Tests (`test_full_e2e.py`)

E2E tests require Blender to be installed. They test real rendering workflows.

### TestSceneWorkflow (5 tests)
- Create, save, and open scene roundtrip preserving all fields
- Scene with objects survives save/load roundtrip
- Scene info reflects accurate object counts after additions

### TestObjectOperations (4 tests)
- Add various mesh types (cube, sphere, cylinder)
- Multiple objects maintain correct ordering

### TestRenderPipeline (6 tests)
- Generate bpy script from scene
- Verify bpy script contains expected commands
- Render to PNG produces valid output (if Blender available)

### TestCLISubprocess (7 tests)
- `--help` prints usage info
- `scene new` creates a scene
- `scene new --json` returns valid JSON output
- `scene profiles` lists available profiles
- `object list` works with --json
- `material list` works
- Full workflow via JSON CLI

## Running Tests

```bash
# Unit tests only (no Blender required)
python3 -m pytest tests/test_core.py -v

# E2E tests (requires Blender installed)
python3 -m pytest tests/test_full_e2e.py -v

# All tests
python3 -m pytest tests/ -v
```

## Test Results (Placeholder)

```
============================= test session starts ==============================
collected ~80 items

test_core.py::TestScene::test_create_default PASSED
test_core.py::TestScene::test_create_with_dimensions PASSED
...
================================ in progress =================================
```
