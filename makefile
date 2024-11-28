run:
    python setup.py check  
    python setup.py sdist 
    python setup.py bdist_wheel --universal    
    twine upload --skip-existing --repository testpypi dist/*
update-pypi:
    # For test pypi repo
    twine upload --skip-existing --repository testpypi dist/*
    # For main pypi repo
    twine upload --skip-existing dist/*
install-scipplan:
    pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ scipplan==0.1.0a33
    twine upload dist/*