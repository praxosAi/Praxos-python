# Praxos Python SDK v0.3.0 Installation Guide

## New in v0.3.0: Intelligent Search
- 🧠 AI-powered query analysis and type detection
- 📅 Automatic temporal anchor extraction  
- 🎯 Smart search strategy routing
- 🔄 Multi-strategy execution for comprehensive results

## Installation Methods

### Method 1: Development Installation (Recommended)
```bash
# Clone or navigate to the repository
cd /path/to/praxos-reboot/Praxos-python

# Install in editable mode
pip install -e .

# Verify installation
python test_intelligent_search.py
```

### Method 2: Standard Installation
```bash
# Navigate to the package directory
cd /path/to/praxos-reboot/Praxos-python

# Install the package
pip install .

# Verify installation
python -c "from praxos_python import SyncClient; print('✅ Installation successful')"
```

### Method 3: Build and Install Wheel
```bash
# Install build tools if needed
pip install build

# Navigate to package directory
cd /path/to/praxos-reboot/Praxos-python

# Build the package
python -m build

# Install the built wheel
pip install dist/Praxos_python-0.3.0-py3-none-any.whl
```

### Method 4: From Git Repository
```bash
# If the repository is published to Git
pip install git+https://github.com/your-org/praxos-reboot.git#subdirectory=Praxos-python
```

## Dependencies

The SDK requires:
- `pydantic` - Data validation and serialization
- `httpx` - HTTP client for API requests

These are automatically installed with the package.

## Verification

After installation, run the test script:

```bash
python test_intelligent_search.py
```

Expected output:
```
Testing Praxos Python SDK v0.3.0 with Intelligent Search
============================================================
✅ Import successful - intelligent search methods available
✅ search() method signature: 22 parameters
✅ intelligent_search() method signature: 6 parameters
✅ Default search modality: intelligent

✅ All expected parameters available: 22 total

🎉 All tests passed! SDK is ready to use.
```

## Quick Start

```python
from praxos_python import SyncClient

# Initialize client
client = SyncClient(
    api_key="your_api_key",
    base_url="https://your-api-endpoint.com"  # Optional
)

# Intelligent search (recommended)
results = client.intelligent_search(
    query="withdrawal amounts in November 2023",
    environment_id="your_environment_id",
    max_results=20
)

# Advanced search with full control
results = client.search(
    query="financial transactions from TD Canada Trust", 
    environment_id="your_environment_id",
    search_modality="intelligent",  # or "fast", "node_vec", "type_vec"
    top_k=10,
    node_type="FinancialTransaction",
    include_graph_context=True,
    temporal_filter={"timepoint_type": "Month", "time_period": "November"}
)

print(f"Found {len(results['hits'])} results")
```

## Search Modalities

- **`intelligent`** ✨ - AI-powered orchestrator (recommended)
- **`fast`** ⚡ - Quick Qdrant vector search  
- **`node_vec`** 🕸️ - Neo4j graph-aware search
- **`vec_edge`** 📎 - Legacy edge-based search
- **`type_vec`** 🏷️ - Type-aware search with classification

## Common Issues

### ImportError after installation
```bash
# Ensure you're in the right environment
pip show Praxos-python

# Reinstall if needed
pip uninstall Praxos-python
pip install -e .
```

### Missing dependencies
```bash
# Install dependencies manually
pip install pydantic httpx
```

### Version conflicts
```bash
# Check installed version
python -c "import praxos_python; print(praxos_python.__version__ if hasattr(praxos_python, '__version__') else 'Version info not available')"

# Force reinstall
pip install --force-reinstall -e .
```

## Development Setup

For development work:

```bash
# Clone the repository
git clone https://github.com/your-org/praxos-reboot.git
cd praxos-reboot/Praxos-python

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install in development mode
pip install -e .

# Install development dependencies (if any)
pip install pytest black flake8

# Run tests
python test_intelligent_search.py
```

## Publishing to PyPI (For Maintainers)

```bash
# Build the package
python -m build

# Upload to PyPI (requires credentials)
pip install twine
twine upload dist/*

# Install from PyPI
pip install Praxos-python==0.3.0
```

## Support

For issues with the SDK:
1. Check this installation guide
2. Run `python test_intelligent_search.py` to verify setup
3. Check the main documentation in `INTELLIGENT_SEARCH_IMPLEMENTATION.md`
4. Contact support at support@praxos.ai