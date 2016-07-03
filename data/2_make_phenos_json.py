#!/usr/bin/env python2

from __future__ import print_function, division, absolute_import

# Load config
import os.path
import imp
my_dir = os.path.dirname(os.path.abspath(__file__))
conf = imp.load_source('conf', os.path.join(my_dir, '../config.config'))

# Activate virtualenv
activate_this = os.path.join(conf.virtualenv_dir, 'bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

import csv
import json
import gzip
import collections
import glob
import re


def get_phenos_from_input_files():
    good_phenos = collections.OrderedDict() # have enough cases
    bad_phenos = {} # don't have enough cases

    sourcefiles = glob.glob(conf.epacts_source_filenames_pattern)
    print('number of sourcefiles matched by {!r}: {}'.format(conf.epacts_source_filenames_pattern, len(sourcefiles)))
    for sourcefile in sourcefiles:
        # TODO: how to make this nicely configurable?  Make `conf.epacts_source_filenames_pattern` a regex with one group that must match pheno_code?
        match = re.search(r'/pheno\.[0-9\.]+?/pheno\.([0-9\.]+?)\.epacts\.gz$', sourcefile)
        assert len(match.groups()) == 1
        phewas_code = match.groups()[0]

        with gzip.open(sourcefile) as f:
            reader = csv.DictReader(f, delimiter='\t')
            first_line = next(reader)
            num_controls, num_cases = int(first_line['NS.CTRL']), int(first_line['NS.CASE'])
            if num_cases >= conf.minimum_num_cases:
                good_phenos[phewas_code] = dict(num_cases=num_cases, num_controls=num_controls)
            else:
                bad_phenos[phewas_code] = True

    print('number of phenos at least {} cases: {}'.format(conf.minimum_num_cases, len(good_phenos)))
    print('number of phenos with fewer than {} cases: {}'.format(conf.minimum_num_cases, len(bad_phenos)))
    if bad_phenos:
        print('example phenos with too few cases:', ', '.join(list(bad_phenos)[:10]))

    assert 1400 <= len(good_phenos) <= 1500
    assert len(bad_phenos) <= 500
    return good_phenos
good_phenos = get_phenos_from_input_files()

# Hide small numbers of cases for identifiability reasons.
for pheno in good_phenos.values():
    for key in ['num_cases', 'num_controls']:
        pheno[key] = '<50' if pheno[key] < 50 else pheno[key]

# Load icd9 info, category_string, and phewas_string for each phewas_code.
for phewas_code in good_phenos:
    good_phenos[phewas_code]['icd9s'] = []
pheno_and_icd9_filename = os.path.join(my_dir, 'PheWAS_code_translation_v1_2.txt')
with open(pheno_and_icd9_filename) as f:
    for icd9 in csv.DictReader(f, delimiter='\t'):

        pheno = good_phenos.get(icd9['phewas_code'], None)
        if pheno is not None:
            pheno['icd9s'].append({
                'icd9_code': icd9['icd9'],
                'icd9_string': icd9['icd9_string'],
            })

            if 'phewas_string' not in pheno:
                pheno['phewas_string'] = icd9['phewas_string']
            else:
                assert pheno['phewas_string'] == icd9['phewas_string']

            if 'category_string' not in pheno:
                pheno['category_string'] = icd9['category_string']
            else:
                assert pheno['category_string'] == icd9['category_string']

for phewas_code in good_phenos:
    assert len(good_phenos[phewas_code]['icd9s']) > 0

with open('phenos.json', 'w') as f:
    json.dump(good_phenos, f, sort_keys=True, indent=0)
