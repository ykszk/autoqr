import io
import zipfile
import pydicom
from pydicom.datadict import keyword_for_tag


def save_as_zip(contents, compresslevel, zip_filename=None):
    '''
    Args:
        contents (iterable): Iterable object that returns (filename, content(bytes))
        compresslevel (int): Compression level for zipping. Specify -1 for no compression.
        zip_filename (str): Filename for zipped contents. If None, bytes is returned.
    '''
    compression = zipfile.ZIP_STORED if compresslevel < 0 else zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(zip_filename,
                         'w',
                         compression,
                         compresslevel=compresslevel) as zf:
        for filename, content in contents:
            zf.writestr(filename, content)


def dcm2bytes(dcm):
    with io.BytesIO() as bio:
        pydicom.dcmwrite(bio, dcm)
        return bio.getvalue()


def dcms2zip(filenames, dcms, compresslevel, zip_filename):
    '''
    Args:
        compresslevel (int): Compression level for zipping. Specify -1 for no compression.
        zip_filename (str): Filename for zipped contents. If None, bytes is returned.
    '''
    generator = zip(filenames, (dcm2bytes(dcm) for dcm in dcms))
    return save_as_zip(generator, compresslevel, zip_filename)


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


class DcmGeneratorFN(object):
    '''
    Args:
        replace_rules (list): list of tuples of (tag, new_value). new_value is either a str or a generator function.
        remove_rules (list): list of tags to remove
    '''
    def __init__(self, fns, replace_rules, remove_rules):
        self.fns = fns
        self.length = len(fns)
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

        fn = self.fns[self._i]
        dcm = pydicom.dcmread(fn)

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
