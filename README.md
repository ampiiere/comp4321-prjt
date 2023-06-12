# COMP4321 Prjt: Set up

#### 1. Setup preferred Virtual env (optional)
- Packages must be installed, loading them into a virtual env would make it easier to delete them later. 

#### 1.5 Install pip (optional)
- Only required if pip is not already installed. 
- Mac/Linux: `python get-pip.py`
- Windows: `py get-pip.py`

#### 2. Pip install packages
- Using pip, install packages (into virtual env). 
- `pip install sqlitedict bs4 requests nltk python-dateutil django`

#### 3. Run crawler.py to crawl page
- `python crawler.py`

#### 4. Run test.py to print results from database
- `python test.py`
- See output results in spider_result.txt

#### 5. move into mysite dir
- `cd mysite`
  
#### 6. Runserver with Django
- `python manage.py runserver`
- Search page at http://127.0.0.1:8000/



