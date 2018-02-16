import sys
import os
import requests
from bs4 import BeautifulSoup
import Levenshtein

ROOT = 'https://archive.ics.uci.edu/ml/'


class Directory():
    def __init__(self, name, data=None):
        self.name = name
        if data is not None:
            if 'modified' in data:
                self.modified = data['modified']
            if 'root' in data:
                self.root = data['root']
            if 'files' in data:
                self.files = data['files']
            if 'sub_directories' in data:
                self.sub_directories = data['sub_directories']

    def set_files(self, files=None):
        self.files = files

    def set_sub_dirs(self, sub_directories):
        self.sub_directories = sub_directories

    def set_name(self, name):
        self.name = name


class File():
    def __init__(self, url, name, last_modified='', size='', description=''):
        self.url = url
        self.name = name
        self.last_modified = last_modified
        self.size = size
        self.description = description


def get_tree(page, dir_name='root'):
    root = Directory(dir_name, {'root': dir_name == 'root'})
    soup = BeautifulSoup(requests.get(page).text, 'html.parser')
    table = soup.find('table')
    rows = table.findAll('tr')[3:-1]
    files = []
    dirs = []
    for row in rows:
        url = row.find('a', href=True)['href']
        if url[-1] == '/':
            cols = [col.get_text().strip() for col in row.findAll('td')[1:]]
            sub_dir = get_tree(page + url, cols[0][:-1])
            dirs.append(sub_dir)
        else:
            cols = [col.get_text().strip() for col in row.findAll('td')[1:]]
            files.append(File(page + url, cols[0], cols[1], cols[2], cols[3]))
    root.set_files(files)
    root.set_sub_dirs(dirs)
    return root


def fix_url(url):
    return url if ROOT in url else ROOT + url


def get_data_sets():
    path = 'datasets.html'
    doc = requests.get(ROOT + path)
    soup = BeautifulSoup(doc.text, 'html.parser')

    rows = soup.findAll('table')[5].findAll('tr')

    datasets = []

    for row in rows[1:]:
        col = row.findAll('a', href=True)[1]
        title = col.get_text()
        url = fix_url(col['href'])
        datasets.append({'title': title, 'url': url})

    # TODO: Fix duplicate results
    return datasets


def get_data_set(page):
    url = page
    dataset_soup = BeautifulSoup(requests.get(url).text, 'html.parser')
    temp = dataset_soup.findAll('font')
    folder_url = ROOT + temp[5].parent['href'][3:]
    return get_tree(folder_url)


def find_exact(name, dataset):
    for data in dataset:
        if data['title'].lower() == name.lower():
            return data


def search(query):
    query = query.lower()
    data = [datum['title'] for datum in get_data_sets()]
    results = []
    for row in data:
        if query in row.lower():
            results.append(row)
        elif Levenshtein.ratio(query, row.lower()) >= 0.6:
            results.append(row)
    return sorted([res.replace(' ', '-').lower() for res in set(results)])


def main():
    args = sys.argv
    if len(args) > 1:
        command = args[1]
        if command == 'search':
            if len(args) > 2:
                option = args[2]
                print('Searching for \'{}\'...'.format(option))
                results = '\n'.join(search(option))
                print()
                print(results)
        elif command == 'list-remote' or command == 'lsr':
            print('Fetching...')
            fetched = [data['title'] for data in get_data_sets()]
            print('\n'.join(list(set(fetched))))
        elif command == 'get':
            if len(args) > 2:
                name = args[2].replace('-', ' ')
                url = find_exact(name, get_data_sets())['url']
                directory = get_data_set(url)
                download(directory, name)
        else:
            print('Invalid Command!')
    else:
        print('Usage')


def download(directory, dataset, path=''):
    print(dataset)
    for file in directory.files:
        response = requests.get(file.url)
        if response.status_code == 200:
            # handle encoding
            fetched_file = response.text
            print(file.name)
            filename = (dataset + path + '/' + file.name).lower()
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            # handle encoding
            try:
                with open(filename, 'w+') as fil:
                    fil.write(fetched_file)
            except UnicodeEncodeError:
                with open(filename, 'w+', encoding="utf-8") as fil:
                    fil.write(fetched_file)
        else:
            print('[ERR] Request for {} failed with code {}'.format(
               file.name, response.status_code
            ))
    for folder in directory.sub_directories:
        download(folder, dataset, path='/' + folder.name)


main()
