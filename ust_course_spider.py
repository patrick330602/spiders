#!/usr/bin/env python3
# HKUST ARR Schedule WebSpider
# Author: Patrick Wu(@patrick330602)
import json
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup as bs

IS_DEBUG = False
DEBUG_COURSE = "ACCT"

course_list = []
dept_links = []
baseJsonStr = {}

if len(sys.argv) > 1:
    if sys.argv[1] == "--debug":
        IS_DEBUG = True


def info_print(input):
    '''Beautify Print
    '''
    print("["+time.strftime("%H:%M:%S", time.localtime())+"]"+input)


def course2deptcode(input):
    '''Convert course code to department code and numerial course code
    '''
    return input[:4], input[(len(input)-4):]


def title2creditname(input):
    '''Convert title to credit and name
    '''
    credit_untrimed = re.search('\([\s\S]+\)', input)
    credit = (re.search('\d', credit_untrimed.group(0))).group(0)
    name_untrimed = re.search('-\s[\s\S]+\s\(', input)
    name = name_untrimed.group(0).replace('- ', '').replace(' (', '')
    return credit, name


def sections2list(input, course_title):
    data_keeper = []
    counter = -1

    rows = input.findChildren(['th', 'tr'])
    for row in rows:
        j = 0
        cells = row.findChildren('td')
        if len(cells) == 9:
            del data_keeper[:]

            for cell in cells:
                value = cell.get_text()
                data_keeper.append(value)

                if IS_DEBUG:
                    print(str(counter+1)+","+str(j)+":"+value)

            baseJsonStr['courses'][course_title]['sections'].append({'name': data_keeper[0],
                                                                     'classes': [{'datetime': data_keeper[1],
                                                                                  'location': data_keeper[2]}],
                                                                     'instructors': data_keeper[3],
                                                                     'quota': data_keeper[4],
                                                                     'enrol': data_keeper[5],
                                                                     'avail': data_keeper[6],
                                                                     'wait': data_keeper[7],
                                                                     'remarks': data_keeper[8].replace("\u00a0", "")})
            counter += 1

        elif len(cells) == 3:
            merged_int = 1

            for cell in cells:
                value = cell.get_text()
                data_keeper[merged_int] = value
                merged_int += 1

                if IS_DEBUG:
                    print("*** "+str(counter+1)+","+str(j)+":"+value)

            baseJsonStr['courses'][course_title]['sections'][counter]['classes'].append(
                {'datetime': data_keeper[1], 'location': data_keeper[2]})


def arr2json(input):
    '''Convert Raw Course HTML to json object
    '''
    course_soup = bs(str(input), 'lxml')
    course_title = course_soup.find('a').get('name')
    course_list.append(course_title)

    info_print(course_title)
    for b_s in course_soup.find_all("br"):
        b_s.replace_with("\n")

    if IS_DEBUG:
        result = open(course_title+".html", "w+")
        result.write(str(course_soup.contents))

    # Overivew
    dept, code = course2deptcode(course_title)
    credit, name = title2creditname(str(course_soup.find('h2').next))

    baseJsonStr['courses'][course_title] = {}
    baseJsonStr['courses'][course_title]['id'] = course_title
    baseJsonStr['courses'][course_title]['department'] = dept
    baseJsonStr['courses'][course_title]['code'] = code
    baseJsonStr['courses'][course_title]['credit'] = credit
    baseJsonStr['courses'][course_title]['name'] = name

    # Details
    detail_data = {}
    baseJsonStr['courses'][course_title]['details'] = {}

    detail_soup = course_soup.find('table', attrs={'width': '400'})

    for row in detail_soup.find_all('tr'):
        headers = row.find('th')
        subdata = row.find('td')

        if str(headers.next) == "INTENDED":
            break

        detail_data[str(headers.next)] = subdata.get_text()

    detail_strings = ['ATTRIBUTES', 'VECTOR', 'PRE-REQUISITE',
                      'CO-REQUISITE', 'PREVIOUS CODE', 'EXCLUSION']
    for dstring in detail_strings:

        if dstring in detail_data:
            content = detail_data[dstring]
            baseJsonStr['courses'][course_title]['details'][dstring.lower()
                                                            ] = content

    desc = detail_data['DESCRIPTION']
    desc = re.sub(r'[\xc2-\xf4][\x80-\xbf]+',
                  lambda m: m.group(0).encode('latin1').decode('utf8'), desc)
    baseJsonStr['courses'][course_title]['details']['description'] = desc

    # Sections
    baseJsonStr['courses'][course_title]['sections'] = []
    sections_soup = course_soup.find('table', attrs={'width': '1012'})
    sections2list(sections_soup, course_title)


def main():
    total_count = 0
    baseJsonStr['courses'] = {}

    info_print("HKUST ARR Schdule WebSpider")
    info_print("Constructing connections...")
    base_req = requests.get("https://w5.ab.ust.hk/wcq/cgi-bin/")
    base_req.encoding = 'utf-8'
    base_res = base_req.text
    base_soup = bs(base_res, 'lxml')
    base_course = base_soup.select("div.depts > a")

    for cotitle in base_course:
        dept_links.append(cotitle.get("href"))

    if IS_DEBUG:
        del dept_links[:]
        dept_links.append('/wcq/cgi-bin/1710/subject/' + DEBUG_COURSE)

    for link in dept_links:
        url = 'https://w5.ab.ust.hk'+link
        req = requests.get(url)
        res = req.text

        soup = bs(res, 'lxml')
        needed_data = soup.select("[class~=course]")
        data_count = 0

        for course in needed_data:
            arr2json(course)
            data_count += 1
            total_count += 1
        info_print("complete retrive "+str(data_count) +
                   " course(s) from "+url+".")

    result = open("courses_list.json", "w+")
    result.write(json.dumps(course_list))
    result = open("courses_dict.json", "w+")
    result.write(json.dumps(baseJsonStr))
    info_print("Action complete. Retrived "+str(total_count)+" course(s).")


if __name__ == "__main__":
    main()
