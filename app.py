

from enum import Enum
from os import path
import xml.etree.cElementTree as ET
import argparse
import json
import re


class InfoPropertyListTags(str, Enum):
    TRUE = 'true'
    FALSE = 'false'
    DICT = 'dict'
    ARRAY = 'array'
    KEY = 'key'
    STRING = 'string'


def _parse_lists(list_to_parse: list) -> list:
    formatted_list = []
    for item in list_to_parse:
        if item.tag == InfoPropertyListTags.TRUE.value:
            formatted_list.append(True)
        elif item.tag == InfoPropertyListTags.FALSE.value:
            formatted_list.append(False)
        elif item.tag == InfoPropertyListTags.DICT.value:
            formatted_list.append(_parse_dicts(item))
        elif item.tag == InfoPropertyListTags.ARRAY.value:
            formatted_list.append(_parse_lists(item))
        else:
            formatted_list.append(item.text)
    return formatted_list


def _parse_dicts(dict_to_parse: dict) -> dict:
    propertyKey = ''
    formatted_dict = {}
    for item in dict_to_parse:
        if item.tag == InfoPropertyListTags.KEY.value:
            propertyKey = item.text
        else:
            if item.tag == InfoPropertyListTags.TRUE.value:
                formatted_dict[propertyKey] = True
            elif item.tag == InfoPropertyListTags.FALSE.value:
                formatted_dict[propertyKey] = False
            elif item.tag == InfoPropertyListTags.DICT.value:
                formatted_dict[propertyKey] = _parse_dicts(item)
            elif item.tag == InfoPropertyListTags.ARRAY.value:
                formatted_dict[propertyKey] = _parse_lists(item)
            else:
                formatted_dict[propertyKey] = item.text
    return formatted_dict


def parse_root_data(root_element) -> dict:
    formatted_dict = {}
    for tag in root_element:
        formatted_dict = _parse_dicts(tag)
    return formatted_dict


def wrap_key_tag(text: str, master_wrapper):
    key_tag = ET.SubElement(master_wrapper, InfoPropertyListTags.KEY)
    key_tag.text = text


def wrap_string_tag(text: str, master_wrapper):
    string_tag = ET.SubElement(master_wrapper, InfoPropertyListTags.STRING)
    string_tag.text = text


def wrap_boolean_tag(value: bool, master_wrapper):
    tag_in_value = 'true' if value else 'false'
    boolean_tag = ET.SubElement(master_wrapper, tag_in_value)


def wrap_dict_tag(dict_to_parse: dict, master_wrapper):
    dict_tag = ET.SubElement(master_wrapper, InfoPropertyListTags.DICT)
    for key, value in dict_to_parse.items():
        if isinstance(value, str):
            wrap_key_tag(key, dict_tag)
            wrap_string_tag(value, dict_tag)
        elif isinstance(value, dict):
            wrap_key_tag(key, dict_tag)
            wrap_dict_tag(value, dict_tag)
        elif isinstance(value, list):
            wrap_key_tag(key, dict_tag)
            wrap_array_tag(value, dict_tag)
        elif isinstance(value, bool):
            wrap_key_tag(key, dict_tag)
            wrap_boolean_tag(value, dict_tag)
        else:
            raise Exception(
                f'Unknown info property list type: {value}')


def wrap_array_tag(list_to_parse: list, master_wrapper):
    array_tag = ET.SubElement(master_wrapper, InfoPropertyListTags.ARRAY)
    for item in list_to_parse:
        if isinstance(item, str):
            wrap_string_tag(item, array_tag)
        elif isinstance(item, dict):
            wrap_dict_tag(item, array_tag)
        elif isinstance(item, list):
            wrap_array_tag(item, array_tag)
        elif isinstance(item, bool):
            wrap_boolean_tag(item, array_tag)
        else:
            raise Exception(
                f'Unknown info property list type: {item}')


def indent(elem, level=0):
    i = "\n" + level*"  "
    j = "\n" + (level-1)*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for subelem in elem:
            indent(subelem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = j
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = j
    return elem


def dict_to_xml(dict_to_parse: dict) -> ET:
    xml_root = ET.Element

    for key, value in dict_to_parse.items():
        splitten_root_wrap = key.split(' ')

        xml_root = ET.Element(
            splitten_root_wrap[0], version=splitten_root_wrap[1].split('=')[1])
        dict_tag = ET.SubElement(
            xml_root, InfoPropertyListTags.DICT.value)

        for main_dict_value in value.values():
            for info_property_key, info_property_value in main_dict_value.items():
                if isinstance(info_property_value, str):
                    wrap_key_tag(info_property_key, dict_tag)
                    wrap_string_tag(info_property_value, dict_tag)
                elif isinstance(info_property_value, dict):
                    wrap_key_tag(info_property_key, dict_tag)
                    wrap_dict_tag(info_property_value, dict_tag)
                elif isinstance(info_property_value, list):
                    wrap_key_tag(info_property_key, dict_tag)
                    wrap_array_tag(info_property_value, dict_tag)
                elif isinstance(info_property_value, bool):
                    wrap_key_tag(info_property_key, dict_tag)
                    wrap_boolean_tag(info_property_value, dict_tag)
                else:
                    raise Exception(
                        f'Unknown info property list type: {info_property_value}')

    xml_tree = ET.ElementTree(xml_root)
    indent(xml_root)
    return xml_tree


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--init', action='store_true',
                        help='initialize json').required = False
    parser.add_argument('plist', type=str,
                        help='path to plist').required = True
    parser.add_argument('json', type=str,
                        help='path to parsed json file').required = True
    return parser.parse_args()


def main():
    args = parse_args()

    info_property_list = ET.parse(args.plist)
    root = info_property_list.getroot()

    root_tag = root.tag
    version_attribute = root.attrib['version']
    p_list_tag = f"{root_tag} version={version_attribute}"

    parsed_root = {
        p_list_tag: {
            'dict': parse_root_data(root)
        }
    }

    initialize = args.init
    path_of_property_list = args.plist
    json_to_parse = args.json

    if initialize:
        with open(json_to_parse, 'w') as info_property_list_json:
            json.dump(parsed_root, info_property_list_json, indent=2)
    else:
        try:
            with open(json_to_parse) as info_property_list_json:
                data = json.load(info_property_list_json)
                if path.exists(path_of_property_list):
                    xml_tree = dict_to_xml(data)
                    xml_tree.write(path_of_property_list)
                    with open(path_of_property_list, 'r+') as file:
                        xml_content = file.read()
                        file.seek(0, 0)
                        doc_type = """<?xml version=\'1.0\' encoding=\'utf-8\'?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd">"""
                        file.write(doc_type.rstrip(
                            '\r\n') + '\n' + xml_content)

                else:
                    raise Exception(
                        f'The given file with {path_of_property_list} does not exist')

        except FileNotFoundError:
            print('File not found please initialize tool with "--init"')


main()
