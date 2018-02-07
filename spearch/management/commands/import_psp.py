import os
import re
import sys
import tempfile
import urllib
from zipfile import ZipFile

import requests
from bs4 import BeautifulSoup, Comment
from django.core.management.base import BaseCommand

from spearch.models import Institution, Speaker, Speech

# probably won't be used
def import_term_zip(url):
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    zips = [a['href'] for a in soup.find_all('a') if a['href'].endswith('.zip')]
    base_url = url.rsplit('/', 1)[0]
    for zip_name in zips:
        zip_url = urllib.parse.urljoin(base_url, 'zip/' + zip_name)
        import_zip(zip_name, zip_url)

# probably won't be used
def import_zip(name, url):
    print('Trying {}'.format(url))
    response = requests.get(url)
    if response.status_code == 200:
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, name)
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            print('Downloaded {}.'.format(zip_path))
            zip_file = ZipFile(zip_path)
            zip_file.extractall(tmp_dir)
            os.chdir(tmp_dir)
            with open('index.htm') as index:
                soup = BeautifulSoup(index, 'html.parser')
                #TODO parse links and import
    else:
        print('Request to {} failed with {}.'.format(response.url,
                                                     response.status_code))
def import_term(url):
    print('importing term {}'.format(url))
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    content = soup.find('div', {'id': 'main-content'})
    day_links = content.find_all('a', href=re.compile(r'\d+schuz/\d+-\d+.html'))
    for dl in day_links:
        print('processing {}'.format(dl['href']))
        import_day(urllib.parse.urljoin(url, dl['href']))

def import_day(url):

    # TODO: This won't capture everything!
    # e.g. for https://www.psp.cz/eknih/2017ps/stenprot/001schuz/1-1.html
    # There are links to e.g.:
    #   https://www.psp.cz/eknih/2017ps/stenprot/001schuz/s001001.htm
    #   https://www.psp.cz/eknih/2017ps/stenprot/001schuz/s001005.htm
    # but not to e.g.:
    #   https://www.psp.cz/eknih/2017ps/stenprot/001schuz/s001002.htm
    # (because no speech starts in that segment since there is a long
    #  speech starting on s001001.htm and ending on s001005.htm)
    # This probably doesn't happen too often but still it should be
    # addressed at some point.

    print('importing day {}'.format(url))
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    content = soup.find('div', {'id': 'main-content'})
    speech_links = content.find_all('a', href=re.compile(r's\d+.htm#r\d+'))
    sections = [link['href'].split('#')[0] for link in speech_links]
    all_speeches = ''
    for sec in sections:
        sec_page = requests.get(urllib.parse.urljoin(url, sec))
        sec_soup = BeautifulSoup(sec_page.text, 'html.parser')
        sec_cont = sec_soup.find('div', {'id': 'main-content'})
        filter_records(sec_cont)
        # we want the children of main-content div, not the div itself
        for ch in sec_cont.children:
            all_speeches += str(ch)
    all_soup = BeautifulSoup(all_speeches, 'html.parser')
    #print(all_soup.prettify())
    current_speech = ''
    current_author = None
    try:
        psp = Institution.objects.get(name='Poslanecká sněmovna')
    except:
        psp = Institution(name='Poslanecká sněmovna')
        psp.save()
    for ch in all_soup.children:
        if (ch.name == 'p' or
            ch.name is None or
            ch.name == 'br' or
            (ch.name == 'div' and 'media-links' in ch['class'])):
            # TODO process it! Append to the current speech or start a new speech
            if ch.name == 'p':
                a = ch.find('a', id=re.compile(r'^r\d+'))
                if a:
                    # new speech
                    #print('{} said:\n{}\n-----\n'.format(current_author,
                    #                                     current_speech[:200]))

                    # insert to the DB
                    import_speech(psp, current_author, current_speech)
                    # TODO add date and link to the speech (psp.cz) somehow
                    current_author = (
                        a.text,
                        urllib.parse.urljoin('https://www.psp.cz', a['href']))
                    current_speech = ch.text
                    continue
            if ch.name is None:
                current_speech += '\n' + ch
            else:
                current_speech += '\n' + ch.text
        else:
            # this is probably an unwanted tag
            print(ch)
            print(ch.name)
            sys.exit(1)
    # last speech
    #print('{} said:\n{}\n-----\n'.format(current_author,
    #                                     current_speech[:200]))

    # insert to the DB
    import_speech(psp, current_author, current_speech)
    # TODO add date and link to the speech (psp.cz) somehow

def import_speech(institution, author, speech):
    """Insert the given speech to the DB."""

    if not author:
        print('Speech "{}" does not have a valid author.'.format(speech))
        return

    #TODO: Remove/extract titles
    try:
        sp = Speaker.objects.get(name=author[0])
    except:
        sp = Speaker(name=author[0], url_psp=author[1])
        sp.save()

    s = Speech(institution=institution, speaker=sp, speaker_title='', #date=...
               speech=speech)
    #print('IMPORTING {}'.format(s))
    s.save()

def is_empty_string(string):
    """Return True if the given string is empty."""
    return not bool(string)

def filter_records(soup):
    # remove comments
    for c in soup.find_all(string=lambda text:isinstance(text, Comment)):
        #print('REMOVING: {}'.format(c))
        c.extract()

    # remove whitespace-only strings
    for t in soup.find_all(string=re.compile('^\s*$')):
        #print('REMOVING: {}'.format(t))
        t.extract()

    # TODO remove empty strings

    # ignore navigation
    for div in soup.find_all('div', {'class': 'document-nav'}):
        #print('REMOVING: {}'.format(div))
        div.decompose()

    # remove info about session pauses - the regex might need some tweaking
    for p in soup.find_all('p', string=re.compile(r'^\s*\(Jednání (přerušeno|skončilo|pokračovalo|zahájeno) (v|ve|od) \d\d?[.:]\d\d( do \d\d?[.:]\d\d)? hodin.\) ?(\*\*\*)?\s*$')):
        #print('REMOVING: {}'.format(p))
        p.decompose()

    # TODO? maybe remove strings like (pokračuje <name>) or (<time> hodin)

    # remove empty links
    for a in soup.find_all('a', string=is_empty_string):
        #print('REMOVING: {}'.format(a))
        a.decompose()

    # remove _d links
    for a in soup.find_all('a', {'id': '_d'}):
        a.decompose()

class Command(BaseCommand):
    help='Import speech data from PSP.'

    def handle(self, *args, **kwargs):
        # TODO drop DB

        #import_term_zip('https://www.psp.cz/eknih/2017ps/stenprot/zip/index.htm')
        import_term('https://www.psp.cz/eknih/2017ps/stenprot/index.htm')


