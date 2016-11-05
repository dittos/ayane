from __future__ import unicode_literals
import ctypes
import _ctypes
import comtypes
import comtypes.client

port = comtypes.client.GetModule("portabledeviceapi.dll")
types = comtypes.client.GetModule("portabledevicetypes.dll")

methods = port.IEnumPortableDeviceObjectIDs._methods_
methods[0] = \
    comtypes.COMMETHOD([], ctypes.HRESULT, 'Next',
              ( ['in'], ctypes.c_ulong, 'cObjects' ),
              ( ['in', 'out'], ctypes.POINTER(ctypes.c_wchar_p), 'pObjIDs' ),  # out -> inout
              ( ['in', 'out'], ctypes.POINTER(ctypes.c_ulong), 'pcFetched' ))
del port.IEnumPortableDeviceObjectIDs.Next
port.IEnumPortableDeviceObjectIDs._methods_ = methods


def define_property_key(fmtid, pid):
    struct = port._tagpropertykey(
        fmtid=comtypes.GUID("{EF6B490D-5CD8-437A-AFFC-DA8B60EE4A3C}"),
        pid=pid
    )
    return comtypes.pointer(struct)

WPD_OBJECT_PARENT_ID = define_property_key(comtypes.GUID("{EF6B490D-5CD8-437A-AFFC-DA8B60EE4A3C}"), 3)
WPD_OBJECT_NAME = define_property_key(comtypes.GUID("{EF6B490D-5CD8-437A-AFFC-DA8B60EE4A3C}"), 4)
WPD_OBJECT_CONTENT_TYPE = define_property_key(comtypes.GUID("{EF6B490D-5CD8-437A-AFFC-DA8B60EE4A3C}"), 7)
WPD_OBJECT_SIZE = define_property_key(comtypes.GUID("{EF6B490D-5CD8-437A-AFFC-DA8B60EE4A3C}"), 11)
WPD_OBJECT_ORIGINAL_FILE_NAME = define_property_key(comtypes.GUID("{EF6B490D-5CD8-437A-AFFC-DA8B60EE4A3C}"), 12)

WPD_CONTENT_TYPE_FOLDER = comtypes.GUID("{27E2E392-A111-48E0-AB0C-E17705A05F85}")


def _create_object(impl, clsctx=comtypes.CLSCTX_INPROC_SERVER, **kwargs):
    return comtypes.client.CreateObject(impl, clsctx=clsctx, **kwargs)


class Wpd(object):
    def __init__(self):
        self._manager = _create_object(port.PortableDeviceManager)

    def get_devices(self):
        count_p = ctypes.pointer(ctypes.c_ulong(0))
        self._manager.GetDevices(ctypes.POINTER(ctypes.c_wchar_p)(), count_p)
        if count_p.contents.value == 0:
            return []
        device_ids = (ctypes.c_wchar_p * count_p.contents.value)()
        self._manager.RefreshDeviceList()
        self._manager.GetDevices(device_ids, count_p)
        return [Device(id, self._manager) for id in device_ids]


class Device(object):
    def __init__(self, id, manager):
        self.id = id
        self._manager = manager
        self._device = self._content = None

    def open(self):
        client_info = _create_object(types.PortableDeviceValues)
        device = _create_object(port.PortableDeviceFTM)
        device.Open(self.id, client_info)
        self._device = device
        self._content = device.Content()

    def get_friendly_name(self):
        return self._get_info_string(self._manager.GetDeviceFriendlyName)

    def get_description(self):
        return self._get_info_string(self._manager.GetDeviceDescription)

    def get_manufacturer(self):
        return self._get_info_string(self._manager.GetDeviceManufacturer)

    def iter_objects(self, parent=None, batch_size=16):
        if parent is None:
            parent_id = 'DEVICE'
        else:
            parent_id = parent.id

        enum_object_ids = self._content.EnumObjects(0, parent_id, None)
        object_ids = (ctypes.c_wchar_p * batch_size)()
        size_p = ctypes.pointer(ctypes.c_ulong(0))
        properties = self._content.Properties()
        property_keys = _create_object(
            types.PortableDeviceKeyCollection,
            interface=port.IPortableDeviceKeyCollection
        )
        property_keys.Add(WPD_OBJECT_NAME)
        property_keys.Add(WPD_OBJECT_ORIGINAL_FILE_NAME)
        property_keys.Add(WPD_OBJECT_CONTENT_TYPE)
        property_keys.Add(WPD_OBJECT_SIZE)

        while True:
            enum_object_ids.Next(
                batch_size,
                ctypes.cast(object_ids, ctypes.POINTER(ctypes.c_wchar_p)),
                size_p
            )
            if size_p.contents.value == 0:
                break
            for i in range(size_p.contents.value):
                object_id = object_ids[i]
                property_values = properties.GetValues(object_id, property_keys)
                try:
                    name = property_values.GetStringValue(WPD_OBJECT_ORIGINAL_FILE_NAME)
                except _ctypes.COMError:
                    name = property_values.GetStringValue(WPD_OBJECT_NAME)
                is_folder = property_values.GetGuidValue(WPD_OBJECT_CONTENT_TYPE) == WPD_CONTENT_TYPE_FOLDER
                try:
                    size = property_values.GetUnsignedLargeIntegerValue(WPD_OBJECT_SIZE)
                except _ctypes.COMError:
                    size = None
                yield Object(object_id, name, is_folder, size)

    def delete_objects(self, objects, recursive=False):
        # https://msdn.microsoft.com/en-us/library/windows/desktop/dd388536(v=vs.85).aspx
        VT_LPWSTR = 31
        ids = _create_object(types.PortableDevicePropVariantCollection)
        for obj in objects:
            v = types.tag_inner_PROPVARIANT(vt=VT_LPWSTR)
            # XXX: is this field name consistent in all systems?
            # Use getattr because prefix __ is handled specially
            getattr(v, '__MIDL____MIDL_itf_PortableDeviceTypes_0003_00170001').pwszVal = obj.id
            ids.Add(v)
        self._content.Delete(1 if recursive else 0, ids)

    def _get_info_string(self, func):
        length_p = ctypes.pointer(ctypes.c_ulong(0))
        func(self.id, ctypes.POINTER(ctypes.c_ushort)(), length_p)
        buf = ctypes.create_unicode_buffer(length_p.contents.value)
        func(self.id, ctypes.cast(buf, ctypes.POINTER(ctypes.c_ushort)), length_p)
        return buf.value

    def __repr__(self):
        return '<Device: {}>'.format(self.id)


class Object(object):
    def __init__(self, id, name, is_folder, size):
        self.id = id
        self.name = name
        self.is_folder = is_folder
        self.size = size

    def __repr__(self):
        return (
            '<ObjectRef: {}, id={}, folder={}>'
            .format(self.name, self.id, self.is_folder)
            .encode(errors='replace')
        )
