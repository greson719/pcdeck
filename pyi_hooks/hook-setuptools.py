# Override PyInstaller hook-setuptools to avoid setuptools runtime hooks
excludedimports = ['setuptools', 'setuptools._distutils']
hiddenimports = []
datas = []
