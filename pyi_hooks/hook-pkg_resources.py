# Override PyInstaller hook-pkg_resources to prevent injecting broken pyi_rth_pkgres runtime hook
excludedimports = ['pkg_resources', 'pkg_resources.extern']
hiddenimports = []
datas = []
