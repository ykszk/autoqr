import io
import zipfile
from datetime import datetime
import json
import re
import decimal
from dateutil.relativedelta import relativedelta
import pydicom
from pydicom.datadict import keyword_for_tag
import tqdm


def save_as_zip(contents,
                compresslevel,
                zip_filename=None,
                verbose=False,
                total=None):
    '''
    Args:
        contents (iterable): Iterable object that returns (filename, content(bytes))
        compresslevel (int): Compression level for zipping. Specify -1 for no compression.
        zip_filename (str): Filename for zipped contents. If None, bytes is returned.
        verbose (bool): Show progress bar
        total (int): Passed to tqdm for in verbose mode.
    '''
    compression = zipfile.ZIP_STORED if compresslevel < 0 else zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(zip_filename,
                         'w',
                         compression,
                         compresslevel=compresslevel) as zf:
        for filename, content in tqdm.tqdm(
                contents, total=total) if verbose else contents:
            zf.writestr(filename, content)


def dcm2bytes(dcm):
    with io.BytesIO() as bio:
        pydicom.dcmwrite(bio, dcm)
        return bio.getvalue()


def dcms2zip(filenames, dcms, compresslevel, zip_filename, verbose=False):
    '''
    Args:
        compresslevel (int): Compression level for zipping. Specify -1 for no compression.
        zip_filename (str): Filename for zipped contents. If None, bytes is returned.
    '''
    generator = zip(filenames, (dcm2bytes(dcm) for dcm in dcms))
    return save_as_zip(generator,
                       compresslevel,
                       zip_filename,
                       verbose,
                       total=len(filenames))


def tag2int(tag_str):
    '''
    Convert tag string into a tuple of ints
    e.g. '0008,00010' -> (8,16)

    Args:
        tag_str (str): String representing dicom tag.
    '''
    tags = tag_str.split(',')
    t1, t2 = int(tags[0], 16), int(tags[1], 16)
    return t1, t2


def tag2str(tag):
    '''
    Convert tag (tuple of ints) into string.
    e.g. (8,16) -> '(0008,0010)'
    '''
    return '({:04X},{:04X})'.format(*tag)


def compress_dups(d, k):
    '''
    Compress duplications.

    Args:
       d (dict): input dictionary
       k (func): function that returns value
    '''
    compress = []
    for key, rep_list in d.items():
        first_value = None
        for rep in rep_list:
            old = k(rep)
            if first_value is None:
                first_value = old
                continue

            if first_value != old:
                break

        else:  # all equal
            compress.append(key)

    for key in compress:
        d[key] = d[key][0][1]


def compress_replace(replaces):
    compress_dups(replaces, lambda r: r[1][0])


def compress_remove(remove):
    compress_dups(remove, lambda r: r[1])


class DcmGenerator(object):
    '''
    Args:
        replace_rules (list): list of tuples of (tag, new_value). new_value is either a str or a generator function.
        remove_rules (list): list of tags to remove
    '''
    def __init__(self, dcms, replace_rules, remove_rules):
        self.dcms = dcms
        self.length = len(dcms)
        self.replace_rules = replace_rules
        self.remove_rules = remove_rules
        self._i = 0

    def __len__(self):
        return self.length

    def __iter__(self):
        return self

    def __next__(self):
        if self._i == self.length:
            raise StopIteration()

        dcm = self.dcms[self._i]

        for tag, new_value in self.replace_rules:
            if hasattr(new_value, '__call__'):
                new_value = new_value(dcm)
            if tag[0] == 0x0002:
                dcm.file_meta[tag].value = new_value
            else:
                if tag in dcm:
                    dcm[tag].value = new_value
                else:
                    kw = keyword_for_tag(tag)
                    setattr(dcm, kw, new_value)

        for tag in self.remove_rules:
            if tag in dcm:
                del dcm[tag]

        self._i += 1
        return dcm


def dataset2obj(ds):
    return dict([(str(k).replace(' ', ''), serialize_tag(v.value))
                 for k, v in ds.items()])


def serialize_tag(o):
    if isinstance(o, pydicom.sequence.Sequence):
        return [dataset2obj(ds) for ds in o]
    else:
        return str(o)


def write_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


def read_json(filename):
    with open(filename, encoding='utf-8') as f:
        return json.load(f)


def now(format_str='%Y/%m/%d %H:%M:%S'):
    '''
    Return current datetime in str
    '''
    return datetime.today().strftime(format_str)


def generalize_age(age_str, step_size):
    '''
    Generalize age string. (e.g. '032Y -> 30').
    Return empty string if invalid age string is provided.

    Args:
        age_str (str): String that represents patient age.
        step_size (number): Step size for generalization in years.
    '''
    m = re.match(r'^(\d+)([DWMY])$', age_str)
    if m:
        if m[2] == 'Y':
            age = int(m[1])
        elif m[2] == 'M':
            age = int(m[1]) / 12
        elif m[2] == 'W':
            age = int(m[1]) / 52.1429
        else:  # m[2] == 'D'
            age = int(m[1]) / 365
        generalized = decimal.Decimal(age / step_size).to_integral_value(
            rounding=decimal.ROUND_HALF_UP) * step_size
        return str(int(generalized))
    else:
        return ''


def calc_age(data):
    '''
    Get age from removed information.
    Return [Patient Age (0010,1010)] if it's available.
    Calculate age from [Patient's Birth Date (0010,0030)] and [Study Date (0008,0020)]
    '''
    age_tag = '(0010,1010)'
    if age_tag in data['remove'] and data['remove'][age_tag] != '':
        return data['remove'][age_tag]
    birth_date = data['remove']['(0010,0030)']
    birth_date = datetime.strptime(birth_date, '%Y%m%d')
    study_date = data['remove']['(0008,0020)']
    study_date = datetime.strptime(study_date, '%Y%m%d')
    delta = relativedelta(study_date, birth_date)
    if delta.years > 0:
        return str(delta.years) + 'Y'

    if delta.months > 0:
        return str(delta.months) + 'M'

    if delta.weeks > 0:
        return str(delta.weeks) + 'W'

    if delta.days > 0:
        return str(delta.days) + 'D'

    return ''
