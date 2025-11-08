"""
Dependency Checker and Auto-Installer
======================================

Automatically checks for required dependencies and installs them if missing.
"""

import subprocess
import sys
import importlib.util

# Windows-safe check and cross marks
CHECK = "[OK]"
CROSS = "[X]"


def is_package_installed(package_name: str) -> bool:
    """
    Check if a Python package is installed

    Args:
        package_name: Name of the package to check

    Returns:
        True if installed, False otherwise
    """
    # Handle package name variations
    import_name_map = {
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'requests': 'requests',
        'pydantic': 'pydantic'
    }

    import_name = import_name_map.get(package_name, package_name)

    spec = importlib.util.find_spec(import_name)
    return spec is not None


def install_package(package_name: str) -> bool:
    """
    Install a Python package using pip

    Args:
        package_name: Name of the package to install

    Returns:
        True if installation successful, False otherwise
    """
    try:
        print(f"  Installing {package_name}...", end=' ', flush=True)

        # Run pip install
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package_name],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            print(CHECK)
            return True
        else:
            print(f"{CROSS}\n  Error: {result.stderr}")
            return False

    except Exception as e:
        print(f"{CROSS}\n  Error: {e}")
        return False


def check_and_install_dependencies(requirements_file: str = 'requirements.txt', auto_install: bool = True) -> bool:
    """
    Check for all required dependencies and install if missing

    Args:
        requirements_file: Path to requirements.txt
        auto_install: Whether to automatically install missing packages

    Returns:
        True if all dependencies are satisfied, False otherwise
    """
    print("="*70)
    print("Checking Dependencies")
    print("="*70)

    # Read requirements
    try:
        with open(requirements_file, 'r') as f:
            requirements = f.readlines()
    except FileNotFoundError:
        print(f"{CROSS} Requirements file not found: {requirements_file}")
        return False

    # Parse requirements (handle version specifiers)
    required_packages = []
    for line in requirements:
        line = line.strip()
        if line and not line.startswith('#'):
            # Extract package name (before any version specifier)
            package_name = line.split('>=')[0].split('==')[0].split('<')[0].split('>')[0].strip()
            required_packages.append((package_name, line))

    if not required_packages:
        print("No dependencies specified in requirements.txt")
        return True

    # Check each package
    missing_packages = []
    installed_packages = []

    for package_name, full_spec in required_packages:
        if is_package_installed(package_name):
            print(f"{CHECK} {package_name}")
            installed_packages.append(package_name)
        else:
            print(f"{CROSS} {package_name} (not installed)")
            missing_packages.append(full_spec)

    print("")

    # If all installed, we're done
    if not missing_packages:
        print(f"{CHECK} All dependencies satisfied!")
        print("="*70)
        print("")
        return True

    # Handle missing packages
    if not auto_install:
        print(f"{CROSS} Missing {len(missing_packages)} package(s)")
        print("  Run: pip install -r requirements.txt")
        print("="*70)
        print("")
        return False

    # Auto-install missing packages
    print(f"Installing {len(missing_packages)} missing package(s)...")
    print("")

    failed_packages = []
    for package_spec in missing_packages:
        if not install_package(package_spec):
            failed_packages.append(package_spec)

    print("")

    # Report results
    if failed_packages:
        print(f"{CROSS} Failed to install {len(failed_packages)} package(s):")
        for pkg in failed_packages:
            print(f"  - {pkg}")
        print("")
        print("Please install manually:")
        print(f"  pip install -r {requirements_file}")
        print("="*70)
        print("")
        return False
    else:
        print(f"{CHECK} All dependencies installed successfully!")
        print("="*70)
        print("")
        return True


if __name__ == "__main__":
    """Test the dependency checker"""
    import argparse

    parser = argparse.ArgumentParser(description="Check and install dependencies")
    parser.add_argument('--no-install', action='store_true',
                       help='Only check, do not auto-install')
    args = parser.parse_args()

    success = check_and_install_dependencies(auto_install=not args.no_install)
    sys.exit(0 if success else 1)
