# mypy: ignore-errors
# pylint: disable=too-many-lines,too-few-public-methods,too-many-instance-attributes,invalid-name
# pylint: disable=fixme
import contextlib
import ctypes
import dataclasses
import datetime
import enum
import functools
import os
import sys
import time
from ctypes.wintypes import (
    BOOL,
    BYTE,
    DWORD,
    HANDLE,
    HMODULE,
    LARGE_INTEGER,
    LONG,
    LPDWORD,
    LPHANDLE,
    LPVOID,
    LPWSTR,
    PDWORD,
    ULONG,
    USHORT,
    WORD,
)
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from . import _cache, _util
from ._errors import TimeoutExpired

if TYPE_CHECKING:  # pragma: no cover
    from ._process import Process


MAX_PATH = 260

PROCESS_CREATE_PROCESS = 0x0080
PROCESS_CREATE_THREAD = 0x0002
PROCESS_DUP_HANDLE = 0x0040
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_SET_INFORMATION = 0x0200
PROCESS_SET_QUOTA = 0x0100
PROCESS_SUSPEND_RESUME = 0x0800
PROCESS_TERMINATE = 0x0001
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
THREAD_QUERY_INFORMATION = 0x0040
THREAD_QUERY_LIMITED_INFORMATION = 0x0800
THREAD_SUSPEND_RESUME = 0x0002
SYNCHRONIZE = 0x00100000

READ_CONTROL = 0x20000
STANDARD_RIGHTS_READ = READ_CONTROL
TOKEN_QUERY = 0x8
TOKEN_READ = STANDARD_RIGHTS_READ | TOKEN_QUERY

DUPLICATE_SAME_ACCESS = 0x2

WAIT_TIMEOUT = 0x102
WAIT_OBJECT_0 = 0x0

STATUS_PENDING = 0x103
STILL_ACTIVE = STATUS_PENDING

INFINITE = 0xFFFFFFFF
MAXIMUM_WAIT_OBJECTS = 64

TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPTHREAD = 0x00000004

SystemProcessInformation = 5
SystemHandleInformation = 16
SystemExtendedHandleInformation = 64

ProcessBasicInformation = 0

RelationProcessorCore = 0

BatteryInformation = 0
BatteryTemperature = 2
BatteryDeviceName = 4

ProcessorInformation = 11

TokenUser = 1

SidTypeUser = 1

STATUS_INFO_LENGTH_MISMATCH = 0xC0000004

ERROR_INVALID_PARAMETER = 87
ERROR_INSUFFICIENT_BUFFER = 122
ERROR_NO_MORE_ITEMS = 259

DIGCF_PRESENT = 0x2
DIGCF_DEVICEINTERFACE = 0x10

ALL_PROCESSOR_GROUPS = 0xFFFF

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
OPEN_EXISTING = 3

BATTERY_CHARGING = 0x4
BATTERY_CRITICAL = 0x8
BATTERY_DISCHARGING = 0x2
BATTERY_POWER_ON_LINE = 0x1

BATTERY_CAPACITY_RELATIVE = 0x40000000

BATTERY_UNKNOWN_RATE = 0x80000000
BATTERY_UNKNOWN_CAPACITY = 0xFFFFFFFF


def CTL_CODE(devtype: int, function: int, method: int, access: int) -> int:
    return (devtype << 16) | (access << 14) | (function << 2) | method


FILE_DEVICE_BATTERY = 0x29
METHOD_BUFFERED = 0
FILE_READ_ACCESS = 0x1
IOCTL_BATTERY_QUERY_TAG = CTL_CODE(FILE_DEVICE_BATTERY, 0x10, METHOD_BUFFERED, FILE_READ_ACCESS)
IOCTL_BATTERY_QUERY_INFORMATION = CTL_CODE(
    FILE_DEVICE_BATTERY, 0x11, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_BATTERY_QUERY_STATUS = CTL_CODE(FILE_DEVICE_BATTERY, 0x13, METHOD_BUFFERED, FILE_READ_ACCESS)

DWORD32 = ctypes.c_uint32
DWORD64 = ctypes.c_uint64
SIZE_T = ctypes.c_size_t
ULONGLONG = ctypes.c_ulonglong
ULONG_PTR = SIZE_T
DWORD_PTR = ULONG_PTR
PDWORD_PTR = ctypes.POINTER(ULONG_PTR)
DWORDLONG = ULONGLONG

PWSTR = ctypes.c_wchar_p

DWORD_SIZE = ctypes.sizeof(DWORD)
INVALID_HANDLE_VALUE = HANDLE(-1).value

KPRIORITY = LONG
NTSTATUS = ULONG
SYSTEM_INFORMATION_CLASS = ctypes.c_int
PROCESSINFOCLASS = ctypes.c_int


class FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", DWORD),
        ("dwHighDateTime", DWORD),
    ]

    def pack(self) -> float:
        return float((self.dwHighDateTime << 32) + self.dwLowDateTime)

    @classmethod
    def unpack(cls, raw: Union[int, float]) -> "FILETIME":
        raw = int(raw)
        return cls(dwLowDateTime=raw & 0xFFFFFFFF, dwHighDateTime=raw >> 32)

    def to_system_time(self) -> "SYSTEMTIME":
        dest = SYSTEMTIME()
        if _kernel32.FileTimeToSystemTime(ctypes.byref(self), ctypes.byref(dest)):
            return dest
        else:
            raise ctypes.WinError()

    def to_timestamp(self) -> float:
        return self.to_system_time().to_datetime_utc().timestamp()


class SYSTEMTIME(ctypes.Structure):
    _fields_ = [
        ("wYear", WORD),
        ("wMonth", WORD),
        ("wDayOfWeek", WORD),
        ("wDay", WORD),
        ("wHour", WORD),
        ("wMinute", WORD),
        ("wSecond", WORD),
        ("wMilliseconds", WORD),
    ]

    def to_datetime_utc(self) -> datetime.datetime:
        return datetime.datetime(
            self.wYear,
            self.wMonth,
            self.wDay,
            self.wHour,
            self.wMinute,
            self.wSecond,
            self.wMilliseconds * 1000,
            datetime.timezone.utc,
        )


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", DWORD),
        ("PageFaultCount", DWORD),
        ("PeakWorkingSetSize", SIZE_T),
        ("WorkingSetSize", SIZE_T),
        ("QuotaPeakPagedPoolUsage", SIZE_T),
        ("QuotaPagedPoolUsage", SIZE_T),
        ("QuotaPeakNonPagedPoolUsage", SIZE_T),
        ("QuotaNonPagedPoolUsage", SIZE_T),
        ("PagefileUsage", SIZE_T),
        ("PeakPagefileUsage", SIZE_T),
        ("PrivateUsage", SIZE_T),
    ]


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("cntUsage", DWORD),
        ("th32ProcessID", DWORD),
        ("th32DefaultHeapID", ULONG_PTR),
        ("th32ModuleID", DWORD),
        ("cntThreads", DWORD),
        ("th32ParentProcessID", DWORD),
        ("pcPriClassBase", LONG),
        ("dwFlags", DWORD),
        ("szExeFile", (ctypes.c_char * MAX_PATH)),
    ]


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("cntUsage", DWORD),
        ("th32ThreadID", DWORD),
        ("th32OwnerProcessID", DWORD),
        ("tpBasePri", LONG),
        ("tpDeltaPri", LONG),
        ("dwFlags", DWORD),
    ]


class STRING(ctypes.Structure):
    _fields_ = [
        ("Length", USHORT),
        ("MaximumLength", USHORT),
        ("Buffer", ctypes.c_void_p),
    ]


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [
        ("Length", USHORT),
        ("MaximumLength", USHORT),
        ("Buffer", ctypes.c_void_p),
    ]

    def to_str(self) -> str:
        return ctypes.wstring_at(self.Buffer, self.Length // ctypes.sizeof(ctypes.c_wchar))


class SYSTEM_PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("NextEntryOffset", ULONG),
        ("NumberOfThreads", ULONG),
        ("WorkingSetPrivateSize", LARGE_INTEGER),
        ("HardFaultCount", ULONG),
        ("NumberOfThreadsHighWatermark", ULONG),
        ("CycleTime", ULONGLONG),
        ("CreateTime", LARGE_INTEGER),
        ("UserTime", LARGE_INTEGER),
        ("KernelTime", LARGE_INTEGER),
        ("ImageName", UNICODE_STRING),
        ("BasePriority", KPRIORITY),
        ("UniqueProcessId", HANDLE),
        ("InheritedFromUniqueProcessId", HANDLE),
        ("HandleCount", ULONG),
        ("SessionId", ULONG),
        ("UniqueProcessKey", ULONG_PTR),
        ("PeakVirtualSize", SIZE_T),
        ("VirtualSize", SIZE_T),
        ("PageFaultCount", ULONG),
        ("PeakWorkingSetSize", SIZE_T),
        ("WorkingSetSize", SIZE_T),
        ("QuotaPeakPagedPoolUsage", SIZE_T),
        ("QuotaPagedPoolUsage", SIZE_T),
        ("QuotaPeakNonPagedPoolUsage", SIZE_T),
        ("QuotaNonPagedPoolUsage", SIZE_T),
        ("PagefileUsage", SIZE_T),
        ("PeakPagefileUsage", SIZE_T),
        ("PrivatePageCount", SIZE_T),
        ("ReadOperationCount", LARGE_INTEGER),
        ("WriteOperationCount", LARGE_INTEGER),
        ("OtherOperationCount", LARGE_INTEGER),
        ("ReadTransferCount", LARGE_INTEGER),
        ("WriteTransferCount", LARGE_INTEGER),
        ("OtherTransferCount", LARGE_INTEGER),
    ]

    @property
    def pid(self) -> int:
        return self.UniqueProcessId or 0

    @property
    def ppid(self) -> int:
        return self.InheritedFromUniqueProcessId or 0


class CLIENT_ID(ctypes.Structure):
    _fields_ = [
        ("UniqueProcess", HANDLE),
        ("UniqueThread", HANDLE),
    ]


class SYSTEM_THREAD_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("KernelTime", LARGE_INTEGER),
        ("UserTime", LARGE_INTEGER),
        ("CreateTime", LARGE_INTEGER),
        ("WaitTime", ULONG),
        ("StartAddress", ctypes.c_void_p),
        ("ClientId", CLIENT_ID),
        ("Priority", LONG),
        ("BasePriority", LONG),
        ("ContextSwitches", ULONG),
        ("ThreadState", ULONG),
        ("WaitReason", ULONG),
    ]

    @property
    def pid(self) -> int:
        return self.ClientId.UniqueProcess or 0

    @property
    def tid(self) -> int:
        return self.ClientId.UniqueThread or 0


class SYSTEM_HANDLE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Count", ULONG),
    ]


class SYSTEM_HANDLE_ENTRY(ctypes.Structure):
    _fields_ = [
        ("OwnerPid", ULONG),
        ("ObjectType", BYTE),
        ("HandleFlags", BYTE),
        ("HandleValue", USHORT),
        ("ObjectPointer", ctypes.c_void_p),
        ("AccessMask", ULONG),
    ]


class SYSTEM_HANDLE_INFORMATION_EX(ctypes.Structure):
    _fields_ = [
        ("Count", ULONG_PTR),
        ("Reserved", ULONG_PTR),
    ]


class SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX(ctypes.Structure):
    _fields_ = [
        ("Object", ctypes.c_void_p),
        ("UniqueProcessId", ULONG_PTR),
        ("HandleValue", ULONG_PTR),
        ("GrantedAccess", ULONG),
        ("CreatorBackTraceIndex", USHORT),
        ("ObjectTypeIndex", USHORT),
        ("HandleAttributes", ULONG),
        ("Reserved", ULONG),
    ]


class CURDIR(ctypes.Structure):
    _fields_ = [
        ("DosPath", UNICODE_STRING),
        ("Handle", ctypes.c_void_p),
    ]


class RTL_DRIVE_LETTER_CURDIR(ctypes.Structure):
    _fields_ = [
        ("Flags", USHORT),
        ("Length", USHORT),
        ("TimeStamp", ULONG),
        ("DosPath", STRING),
    ]


class RTL_USER_PROCESS_PARAMETERS(ctypes.Structure):
    _fields_ = [
        ("MaximumLength", ULONG),
        ("Length", ULONG),
        ("Flags", ULONG),
        ("DebugFlags", ULONG),
        ("ConsoleHandle", ctypes.c_void_p),
        ("ConsoleFlags", ULONG),
        ("StandardInput", ctypes.c_void_p),
        ("StandardOutput", ctypes.c_void_p),
        ("StandardError", ctypes.c_void_p),
        ("CurrentDirectory", CURDIR),
        ("DllPath", UNICODE_STRING),
        ("ImagePathName", UNICODE_STRING),
        ("CommandLine", UNICODE_STRING),
        ("Environment", ctypes.c_void_p),
        ("StartingX", ULONG),
        ("StartingY", ULONG),
        ("CountX", ULONG),
        ("CountY", ULONG),
        ("CountCharsX", ULONG),
        ("CountCharsY", ULONG),
        ("FillAttribute", ULONG),
        ("WindowFlags", ULONG),
        ("ShowWindowFlags", ULONG),
        ("WindowTitle", UNICODE_STRING),
        ("DesktopInfo", UNICODE_STRING),
        ("ShellInfo", UNICODE_STRING),
        ("RuntimeData", UNICODE_STRING),
        ("CurrentDirectores", (RTL_DRIVE_LETTER_CURDIR * 32)),
        ("EnvironmentSize", ULONGLONG),
    ]


class PEB(ctypes.Structure):
    if sys.maxsize > 2**32:
        _fields_ = [
            ("Reserved1", (BYTE * 2)),
            ("BeingDebugged", BYTE),
            ("Reserved2", (BYTE * 21)),
            ("LoaderData", ctypes.c_void_p),
            ("ProcessParameters", ctypes.c_void_p),
            ("Reserved3", (BYTE * 520)),
            ("PostProcessInitRoutine", ctypes.c_void_p),
            ("Reserved4", (BYTE * 136)),
            ("SessionId", ULONG),
        ]
    else:
        _fields_ = [
            ("Reserved1", (BYTE * 2)),
            ("BeingDebugged", BYTE),
            ("Reserved2", (BYTE * 1)),
            ("Reserved3", (ctypes.c_void_p * 2)),
            ("LoaderData", ctypes.c_void_p),
            ("ProcessParameters", ctypes.c_void_p),
            ("Reserved4", (BYTE * 3)),
            ("AtlThunkSListPtr", ctypes.c_void_p),
            ("Reserved5", ctypes.c_void_p),
            ("Reserved6", ULONG),
            ("Reserved7", ctypes.c_void_p),
            ("Reserved8", ULONG),
            ("AtlThunkSListPtr32", ULONG),
            ("Reserved9", (ctypes.c_void_p * 45)),
            ("Reserved10", (BYTE * 96)),
            ("PostProcessInitRoutine", ctypes.c_void_p),
            ("Reserved11", (BYTE * 128)),
            ("Reserved12", (ctypes.c_void_p * 1)),
            ("SessionId", ULONG),
        ]


class PROCESS_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Reserved1", ctypes.c_void_p),
        ("PebBaseAddress", ctypes.c_void_p),
        ("Reserved2", (ctypes.c_void_p * 2)),
        ("UniqueProcessId", ULONG_PTR),
        ("Reserved3", ctypes.c_void_p),
    ]


class SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX(ctypes.Structure):
    _fields_ = [
        ("Relationship", ctypes.c_int),
        ("Size", DWORD),
        # We don't need the rest of the fields because Size gives us the actual structure size
    ]


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", DWORD),
        ("dwMemoryLoad", DWORD),
        ("ullTotalPhys", DWORDLONG),
        ("ullAvailPhys", DWORDLONG),
        ("ullTotalPageFile", DWORDLONG),
        ("ullAvailPageFile", DWORDLONG),
        ("ullTotalVirtual", DWORDLONG),
        ("ullAvailVirtual", DWORDLONG),
        ("ullAvailExtendedVirtual", DWORDLONG),
    ]


class PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("cb", DWORD),
        ("CommitTotal", SIZE_T),
        ("CommitLimit", SIZE_T),
        ("CommitPeak", SIZE_T),
        ("PhysicalTotal", SIZE_T),
        ("PhysicalAvailable", SIZE_T),
        ("SystemCache", SIZE_T),
        ("KernelTotal", SIZE_T),
        ("KernelPaged", SIZE_T),
        ("KernelNonpaged", SIZE_T),
        ("PageSize", SIZE_T),
        ("HandleCount", DWORD),
        ("ProcessCount", DWORD),
        ("ThreadCount", DWORD),
    ]


class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Sid", ctypes.c_void_p),
        ("Attributes", DWORD),
    ]


class TOKEN_USER(ctypes.Structure):
    _fields_ = [
        ("User", SID_AND_ATTRIBUTES),
    ]


class MODULEINFO(ctypes.Structure):
    _fields_ = [
        ("lpBaseOfDll", LPVOID),
        ("SizeOfImage", DWORD),
        ("EntryPoint", LPVOID),
    ]


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", BYTE),
        ("BatteryFlag", BYTE),
        ("BatteryLifePercent", BYTE),
        ("SystemStatusFlag", BYTE),
        ("BatteryLifeTime", DWORD),
        ("BatteryFullLifeTime", DWORD),
    ]


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ULONG),
        ("Data2", USHORT),
        ("Data3", USHORT),
        ("Data4", (ctypes.c_ubyte * 8)),
    ]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", DWORD),
        ("Reserved", ULONG_PTR),
    ]


class SP_DEVICE_INTERFACE_DETAIL_DATA_A(ctypes.Structure):
    _fields_ = [
        ("cbSize", DWORD),
        ("DevicePath", (ctypes.c_byte * 1)),
    ]


class PROCESSOR_POWER_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Number", ULONG),
        ("MaxMhz", ULONG),
        ("CurrentMhz", ULONG),
        ("MhzLimit", ULONG),
        ("MaxIdleState", ULONG),
        ("CurrentIdleState", ULONG),
    ]


class BATTERY_WAIT_STATUS(ctypes.Structure):
    _fields_ = [
        ("BatteryTag", ULONG),
        ("Timeout", ULONG),
        ("PowerState", ULONG),
        ("LowCapacity", ULONG),
        ("HighCapacity", ULONG),
    ]


class BATTERY_STATUS(ctypes.Structure):
    _fields_ = [
        ("PowerState", ULONG),
        ("Capacity", ULONG),
        ("Voltage", ULONG),
        ("Rate", LONG),
    ]


class BATTERY_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Capabilities", ULONG),
        ("Technology", ctypes.c_byte),
        ("Reserved", (ctypes.c_char * 3)),
        ("Chemistry", (ctypes.c_char * 4)),
        ("DesignedCapacity", ULONG),
        ("FullChargedCapacity", ULONG),
        ("DefaultAlert1", ULONG),
        ("DefaultAlert2", ULONG),
        ("CriticalBias", ULONG),
        ("CycleCount", ULONG),
    ]


class BATTERY_QUERY_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BatteryTag", ULONG),
        ("InformationLevel", ctypes.c_int),
        ("AtRate", LONG),
    ]


GUID_DEVCLASS_BATTERY = GUID(
    0x72631E54, 0x78A4, 0x11D0, (0xBC, 0xF7, 0x00, 0xAA, 0x00, 0xB7, 0xB3, 0x2A)
)

LPFILETIME = ctypes.POINTER(FILETIME)
LPSYSTEMTIME = ctypes.POINTER(SYSTEMTIME)
LPTHREADENTRY32 = ctypes.POINTER(THREADENTRY32)

_kernel32 = ctypes.WinDLL("kernel32")
_shell32 = ctypes.WinDLL("shell32")
_powrprof = ctypes.WinDLL("powrprof")
_advapi32 = ctypes.WinDLL("advapi32")
_psapi = ctypes.WinDLL("psapi")
_setupapi = ctypes.WinDLL("setupapi")
_ntdll = ctypes.WinDLL("ntdll")

_kernel32.GetTickCount64.argtypes = ()
_kernel32.GetTickCount64.restype = ctypes.c_ulonglong

_kernel32.QueryUnbiasedInterruptTime.argtypes = (ctypes.POINTER(ctypes.c_ulonglong),)
_kernel32.QueryUnbiasedInterruptTime.restype = BOOL

_kernel32.OpenProcess.argtypes = (DWORD, BOOL, DWORD)
_kernel32.OpenProcess.restype = HANDLE

_kernel32.OpenProcessToken.argtypes = (HANDLE, DWORD, ctypes.POINTER(HANDLE))
_kernel32.OpenProcessToken.restype = BOOL

_kernel32.DuplicateHandle.argtypes = (HANDLE, HANDLE, HANDLE, LPHANDLE, DWORD, BOOL, DWORD)
_kernel32.DuplicateHandle.restype = BOOL

_kernel32.GetCurrentProcess.argtypes = ()
_kernel32.GetCurrentProcess.restype = HANDLE

_kernel32.CloseHandle.argtypes = (HANDLE,)
_kernel32.CloseHandle.restype = BOOL

_kernel32.TerminateProcess.argtypes = (HANDLE, ctypes.c_uint)
_kernel32.TerminateProcess.restype = BOOL

_kernel32.GetProcessTimes.argtypes = (HANDLE, LPFILETIME, LPFILETIME, LPFILETIME, LPFILETIME)
_kernel32.GetProcessTimes.restype = BOOL

_kernel32.FileTimeToSystemTime.argtypes = (LPFILETIME, LPSYSTEMTIME)
_kernel32.FileTimeToSystemTime.restype = BOOL

_kernel32.GetThreadTimes.argtypes = (HANDLE, LPFILETIME, LPFILETIME, LPFILETIME, LPFILETIME)
_kernel32.GetThreadTimes.restype = BOOL

_kernel32.QueryFullProcessImageNameW.argtypes = (HANDLE, DWORD, ctypes.c_wchar_p, PDWORD)
_kernel32.QueryFullProcessImageNameW.restype = BOOL

_kernel32.OpenThread.argtypes = (DWORD, BOOL, DWORD)
_kernel32.OpenThread.restype = HANDLE

_kernel32.CreateToolhelp32Snapshot.argtypes = (DWORD, DWORD)
_kernel32.CreateToolhelp32Snapshot.restype = HANDLE

_kernel32.Thread32First.argtypes = (HANDLE, LPTHREADENTRY32)
_kernel32.Thread32First.restype = BOOL

_kernel32.Thread32Next.argtypes = (HANDLE, LPTHREADENTRY32)
_kernel32.Thread32Next.restype = BOOL

_kernel32.SuspendThread.argtypes = (HANDLE,)
_kernel32.SuspendThread.restype = DWORD

_kernel32.ResumeThread.argtypes = (HANDLE,)
_kernel32.ResumeThread.restype = DWORD

_kernel32.Wow64SuspendThread.argtypes = (HANDLE,)
_kernel32.Wow64SuspendThread.restype = DWORD

_kernel32.ReadProcessMemory.argtypes = (
    HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    SIZE_T,
    ctypes.POINTER(SIZE_T),
)
_kernel32.ReadProcessMemory.restype = BOOL

_kernel32.LocalFree.argtypes = (HANDLE,)
_kernel32.LocalFree.restype = HANDLE

_kernel32.GetLogicalProcessorInformationEx.argtypes = (ctypes.c_int, ctypes.c_void_p, PDWORD)
_kernel32.GetLogicalProcessorInformationEx.restype = BOOL

_kernel32.GlobalMemoryStatusEx.argtypes = (ctypes.POINTER(MEMORYSTATUSEX),)
_kernel32.GlobalMemoryStatusEx.restype = BOOL

_kernel32.GetPriorityClass.argtypes = (HANDLE,)
_kernel32.GetPriorityClass.restype = DWORD

_kernel32.SetPriorityClass.argtypes = (HANDLE, DWORD)
_kernel32.SetPriorityClass.restype = BOOL

_kernel32.GetExitCodeProcess.argtypes = (HANDLE, PDWORD)
_kernel32.GetExitCodeProcess.restype = BOOL

_kernel32.WaitForSingleObject.argtypes = (HANDLE, DWORD)
_kernel32.WaitForSingleObject.restype = DWORD

_kernel32.WaitForMultipleObjects.argtypes = (DWORD, ctypes.POINTER(HANDLE), BOOL, DWORD)
_kernel32.WaitForMultipleObjects.restype = DWORD

_kernel32.GetSystemPowerStatus.argtypes = (ctypes.POINTER(SYSTEM_POWER_STATUS),)
_kernel32.GetSystemPowerStatus.restype = BOOL

_shell32.CommandLineToArgvW.argtypes = (ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int))
_shell32.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)

_advapi32.GetTokenInformation.argtypes = (HANDLE, ctypes.c_int, ctypes.c_void_p, DWORD, PDWORD)
_advapi32.GetTokenInformation.restype = BOOL

_advapi32.LookupAccountSidW.argtypes = (
    ctypes.c_wchar_p,
    ctypes.c_void_p,
    ctypes.c_wchar_p,
    PDWORD,
    ctypes.c_wchar_p,
    PDWORD,
    ctypes.c_void_p,
)
_advapi32.LookupAccountSidW.restype = BOOL

_psapi.EnumProcesses.argtypes = (PDWORD, DWORD, PDWORD)
_psapi.EnumProcesses.restype = BOOL

_psapi.GetProcessMemoryInfo.argtypes = (HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), DWORD)
_psapi.GetProcessMemoryInfo.restype = BOOL

_psapi.GetPerformanceInfo.argtypes = (ctypes.POINTER(PERFORMANCE_INFORMATION), DWORD)
_psapi.GetPerformanceInfo.restype = BOOL

_psapi.EnumProcessModules.argtypes = (HANDLE, ctypes.POINTER(HMODULE), DWORD, LPDWORD)
_psapi.EnumProcessModules.restype = BOOL

_psapi.GetModuleInformation.argtypes = (HANDLE, HANDLE, ctypes.POINTER(MODULEINFO), DWORD)
_psapi.GetModuleInformation.restype = BOOL

_psapi.GetMappedFileNameW.argtypes = (HANDLE, HMODULE, LPWSTR, DWORD)
_psapi.GetMappedFileNameW.restype = BOOL

_setupapi.SetupDiGetClassDevsW.argtypes = (ctypes.POINTER(GUID), ctypes.c_wchar_p, HANDLE, DWORD)
_setupapi.SetupDiGetClassDevsW.restype = HANDLE

_setupapi.SetupDiEnumDeviceInterfaces.argtypes = (
    HANDLE,
    ctypes.c_void_p,
    ctypes.POINTER(GUID),
    DWORD,
    ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
)
_setupapi.SetupDiEnumDeviceInterfaces.restype = BOOL

_setupapi.SetupDiGetDeviceInterfaceDetailA.argtypes = (
    HANDLE,
    ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
    ctypes.POINTER(SP_DEVICE_INTERFACE_DETAIL_DATA_A),
    DWORD,
    PDWORD,
    ctypes.c_void_p,
)
_setupapi.SetupDiGetDeviceInterfaceDetailA.restype = BOOL

_setupapi.SetupDiDestroyDeviceInfoList.argtypes = (HANDLE,)
_setupapi.SetupDiDestroyDeviceInfoList.restype = BOOL

_kernel32.DeviceIoControl.argtypes = (
    HANDLE,
    DWORD,
    LPVOID,
    DWORD,
    LPVOID,
    DWORD,
    LPDWORD,
    ctypes.c_void_p,
)
_kernel32.DeviceIoControl.restype = BOOL

_kernel32.GetProcessAffinityMask.argtypes = (HANDLE, PDWORD_PTR, PDWORD_PTR)
_kernel32.GetProcessAffinityMask.restype = BOOL

_kernel32.SetProcessAffinityMask.argtypes = (HANDLE, DWORD_PTR)
_kernel32.SetProcessAffinityMask.restype = BOOL

# XXX Are there documented/stable ways to get the same information?

_ntdll.NtQuerySystemInformation.argtypes = (
    SYSTEM_INFORMATION_CLASS,
    ctypes.c_void_p,
    ULONG,
    ctypes.POINTER(ULONG),
)
_ntdll.NtQuerySystemInformation.restype = NTSTATUS

_ntdll.NtQueryInformationProcess.argtypes = (
    HANDLE,
    PROCESSINFOCLASS,
    ctypes.c_void_p,
    ULONG,
    ctypes.POINTER(ULONG),
)
_ntdll.NtQueryInformationProcess.restype = NTSTATUS

_ntdll.NtSuspendProcess.argtypes = (HANDLE,)
_ntdll.NtSuspendProcess.restype = NTSTATUS

_ntdll.NtResumeProcess.argtypes = (HANDLE,)
_ntdll.NtResumeProcess.restype = NTSTATUS


@dataclasses.dataclass
class VirtualMemoryInfo:  # pylint: disable=too-many-instance-attributes
    total: int
    available: int
    used: int
    free: int

    @property
    def percent(self) -> float:
        return 100 - self.available * 100.0 / self.total


@dataclasses.dataclass
class DiskUsage:
    total: int
    used: int
    free: int

    def percent(self) -> float:
        return self.used * 100.0 / (self.used + self.free)


@dataclasses.dataclass
class ProcessMemoryInfo:  # pylint: disable=too-many-instance-attributes
    num_page_faults: int
    peak_wset: int
    wset: int
    peak_paged_pool: int
    paged_pool: int
    peak_nonpaged_pool: int
    nonpaged_pool: int
    pagefile: int
    peak_pagefile: int
    private: int

    @property
    def rss(self) -> int:
        return self.wset

    @property
    def vms(self) -> int:
        return self.pagefile


# @dataclasses.dataclass
# class ProcessMemoryMap:
#     path: str
#     addr_start: int
#     addr_end: int
#     perms: str
#     rss: int


# @dataclasses.dataclass
# class ProcessMemoryMapGrouped:
#     path: str
#     rss: int


PowerSupplySensorInfo = _util.PowerSupplySensorInfo
ACPowerInfo = _util.ACPowerInfo
BatteryInfo = _util.BatteryInfo
BatteryStatus = _util.BatteryStatus

ProcessStatus = _util.ProcessStatus
ProcessCPUTimes = _util.ProcessCPUTimes
ProcessOpenFile = _util.ProcessOpenFile
ThreadInfo = _util.ThreadInfo


class PriorityClass(enum.Enum):
    ABOVE_NORMAL = 0x8000
    BELOW_NORMAL = 0x4000
    HIGH = 0x80
    IDLE = 0x40
    NORMAL = 0x20
    REALTIME = 0x100


F = TypeVar("F", bound=Callable[..., Any])  # pylint: disable=invalid-name


def _is_access_error(ex: OSError) -> bool:
    return (
        ex.errno is None
        and ex.winerror is None
        and len(ex.args) == 1
        and "access violation" in ex.args[0]
    )


def _translate_access_errors(func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except OSError as ex:
            if _is_access_error(ex):
                raise PermissionError from ex
            else:
                raise

    return cast(F, wrapper)  # pytype: disable=invalid-typevar


@contextlib.contextmanager
def _pid_handle(pid: int, access_flags: int) -> Iterator[ctypes.c_void_p]:
    if pid == 0:
        raise PermissionError
    elif pid < 0:
        raise ProcessLookupError

    handle = _kernel32.OpenProcess(access_flags, False, pid)
    if handle is None:
        e = ctypes.WinError()
        if e.winerror == ERROR_INVALID_PARAMETER:  # pylint: disable=no-member
            e = ProcessLookupError()
        raise e

    try:
        yield handle
    finally:
        _kernel32.CloseHandle(handle)


def _proc_check_alive(handle: ctypes.c_void_p) -> None:
    # Poll with a zero timeout
    res = _kernel32.WaitForSingleObject(handle, 0)
    if res != WAIT_TIMEOUT:
        raise ProcessLookupError if res == WAIT_OBJECT_0 else ctypes.WinError()


def _handle_ntstatus_code(code: int) -> None:
    if 0 <= code <= 0x7FFFFFFF:
        # Success or informational type
        return
    elif code <= 0xBFFFFFFF:
        # Warning type
        return
    else:
        raise OSError("NTSTATUS code {}".format(code))


def _retry_ntsysteminformation(
    cls: int, initsize: int, padding: int
) -> "ctypes.Array[ctypes.c_char]":
    bufsize = initsize
    reqsize = ULONG()

    while True:
        buf = (ctypes.c_char * bufsize)()
        status = _ntdll.NtQuerySystemInformation(cls, buf, bufsize, ctypes.byref(reqsize))

        if status == STATUS_INFO_LENGTH_MISMATCH:
            # Not long enough; resize (with some padding) and try again
            bufsize = reqsize.value + padding
        else:
            _handle_ntstatus_code(status)
            return buf.raw[: reqsize.value]


def _list_handleinfos() -> Iterable[SYSTEM_HANDLE_ENTRY]:
    buf = _retry_ntsysteminformation(
        SystemHandleInformation,
        500 * ctypes.sizeof(SYSTEM_HANDLE_ENTRY),
        100 * ctypes.sizeof(SYSTEM_HANDLE_ENTRY),
    )
    count = SYSTEM_HANDLE_INFORMATION.from_buffer_copy(buf).Count
    return (SYSTEM_HANDLE_ENTRY * count).from_buffer_copy(
        buf, ctypes.sizeof(SYSTEM_HANDLE_INFORMATION)
    )


def _list_handleinfos_ex() -> Iterable[SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX]:
    buf = _retry_ntsysteminformation(
        SystemExtendedHandleInformation,
        500 * ctypes.sizeof(SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX),
        100 * ctypes.sizeof(SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX),
    )
    count = SYSTEM_HANDLE_INFORMATION_EX.from_buffer_copy(buf).Count
    return (SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX * count).from_buffer_copy(
        buf, ctypes.sizeof(SYSTEM_HANDLE_INFORMATION_EX)
    )


def _iter_sysprocinfos() -> Iterator[
    Tuple[SYSTEM_PROCESS_INFORMATION, List[SYSTEM_THREAD_INFORMATION]]
]:
    buf = _retry_ntsysteminformation(
        SystemProcessInformation,
        500 * ctypes.sizeof(SYSTEM_PROCESS_INFORMATION),
        10 * ctypes.sizeof(SYSTEM_PROCESS_INFORMATION),
    )

    i = 0
    while i < len(buf):
        pinfo = SYSTEM_PROCESS_INFORMATION.from_buffer_copy(buf, i)
        tinfos = (SYSTEM_THREAD_INFORMATION * pinfo.NumberOfThreads).from_buffer_copy(
            buf, i + ctypes.sizeof(pinfo)
        )[:]

        length = pinfo.NextEntryOffset
        yield pinfo, tinfos

        if length == 0:
            break
        i += length


# This MUST be a context manager so it can keep the internal buffers alive while the yielded
# information is in use
@contextlib.contextmanager
def _get_sysprocinfo(
    pid: int,
) -> Iterator[Tuple[SYSTEM_PROCESS_INFORMATION, List[SYSTEM_THREAD_INFORMATION]]]:
    for pinfo, tinfos in _iter_sysprocinfos():
        if pid == pinfo.pid:
            yield pinfo, tinfos
            return

    raise ProcessLookupError


def _iter_procentries() -> Iterator[PROCESSENTRY32]:
    handle = _kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if handle is None:
        raise ctypes.WinError()

    try:
        pe32 = PROCESSENTRY32(dwSize=ctypes.sizeof(PROCESSENTRY32))
        if not _kernel32.Process32First(handle, ctypes.byref(pe32)):
            raise ctypes.WinError()
        yield pe32

        while _kernel32.Process32Next(handle, ctypes.byref(pe32)):
            yield pe32
    finally:
        _kernel32.CloseHandle(handle)


def _get_procentry(pid: int) -> PROCESSENTRY32:
    for pe32 in _iter_procentries():
        if pid == pe32.th32ProcessID:
            return pe32

    raise ProcessLookupError


@_cache.CachedByProcess
@_translate_access_errors
def proc_exe(proc: "Process") -> str:
    try:
        with _pid_handle(proc.pid, PROCESS_QUERY_LIMITED_INFORMATION) as handle:
            buf = (ctypes.c_wchar * MAX_PATH)()
            buflen = DWORD(len(buf))

            if _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(buflen)):
                return buf.value
            else:
                ex = ctypes.WinError()
                if _is_access_error(ex):
                    ex = PermissionError()
                raise ex

    except PermissionError:
        with _get_sysprocinfo(proc.pid) as (pinfo, _):
            return pinfo.ImageName.to_str()


def proc_name(proc: "Process") -> str:
    # pylint: disable=protected-access
    if proc.pid == 0:
        return "System Idle Process"
    elif proc.pid == 4:
        return "System"

    if not hasattr(proc, "_pswindows_name"):
        exe = proc_exe(proc)
        if exe:
            proc._pswindows_name = os.path.basename(exe)
        else:
            proc._pswindows_name = os.fsdecode(_get_procentry(proc.pid).szExeFile)

    return proc._pswindows_name


def proc_ppid(proc: "Process") -> int:
    return _get_procentry(proc.pid).th32ParentProcessID


def proc_num_ctx_switches(proc: "Process") -> int:
    with _get_sysprocinfo(proc.pid) as (_, tinfos):
        return sum(tinfo.ContextSwitches for tinfo in tinfos)


def _read_rtl_params(handle: HANDLE) -> RTL_USER_PROCESS_PARAMETERS:
    pbinfo = PROCESS_BASIC_INFORMATION()
    _handle_ntstatus_code(
        _ntdll.NtQueryInformationProcess(
            handle,
            ProcessBasicInformation,
            ctypes.byref(pbinfo),
            ctypes.sizeof(PROCESS_BASIC_INFORMATION),
            None,
        )
    )

    # We have to follow 2 pointers to read this out of the process's memory

    peb = PEB()
    if not _kernel32.ReadProcessMemory(
        handle, pbinfo.PebBaseAddress, ctypes.byref(peb), ctypes.sizeof(PEB), None
    ):
        raise ctypes.WinError()

    rtl_params = RTL_USER_PROCESS_PARAMETERS()
    if not _kernel32.ReadProcessMemory(
        handle,
        peb.ProcessParameters,
        ctypes.byref(rtl_params),
        ctypes.sizeof(RTL_USER_PROCESS_PARAMETERS),
        None,
    ):
        raise ctypes.WinError()

    return rtl_params


def _read_unicode_string(
    handle: HANDLE, ustr: UNICODE_STRING, *, extra_pad: int = 0
) -> "ctypes.Array[ctypes.c_wchar]":
    buf = (ctypes.c_wchar * (ustr.Length + extra_pad))()
    if not _kernel32.ReadProcessMemory(
        handle,
        ustr.Buffer,
        ctypes.byref(buf),
        ustr.Length,
        None,
    ):
        raise ctypes.WinError()

    return buf


def proc_cmdline(proc: "Process") -> List[str]:
    if proc.pid in (0, 4):
        return []

    with _pid_handle(
        proc.pid, PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ | SYNCHRONIZE
    ) as handle:
        _proc_check_alive(handle)
        rtl_params = _read_rtl_params(handle)
        # 2 wchars padding to (cautiously) make sure it's nul-terminated for CommandLineToArgvW
        cmdline = _read_unicode_string(handle, rtl_params.CommandLine, extra_pad=2)

    nargs = ctypes.c_int()
    arr = _shell32.CommandLineToArgvW(cmdline, ctypes.byref(nargs))
    if arr is None:
        raise ctypes.WinError()

    try:
        return arr[: nargs.value]
    finally:
        if _kernel32.LocalFree(arr):
            raise ctypes.WinError()


def proc_cwd(proc: "Process") -> str:
    with _pid_handle(
        proc.pid, PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ | SYNCHRONIZE
    ) as handle:
        _proc_check_alive(handle)
        return _read_unicode_string(
            handle, _read_rtl_params(handle).CurrentDirectory.DosPath
        ).value.rstrip("\\")


def proc_environ(proc: "Process") -> Dict[str, str]:
    with _pid_handle(
        proc.pid, PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ | SYNCHRONIZE
    ) as handle:
        _proc_check_alive(handle)
        rtl_params = _read_rtl_params(handle)

        buf = (ctypes.c_wchar * (rtl_params.EnvironmentSize // ctypes.sizeof(ctypes.c_wchar)))()
        if not _kernel32.ReadProcessMemory(
            handle,
            rtl_params.Environment,
            ctypes.byref(buf),
            ctypes.sizeof(buf),
            None,
        ):
            raise ctypes.WinError()

    return _util.parse_environ_bytes(buf[:].encode())


def proc_status(proc: "Process") -> ProcessStatus:
    if proc.pid in (0, 4) or proc.pid == os.getpid():
        return ProcessStatus.RUNNING

    # Check if the process has died
    try:
        with _pid_handle(proc.pid, SYNCHRONIZE) as handle:
            _proc_check_alive(handle)
    except PermissionError:
        pass

    return ProcessStatus.RUNNING


def proc_username(proc: "Process") -> str:
    with _pid_handle(proc.pid, PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE) as phandle:
        _proc_check_alive(phandle)

        thandle = HANDLE()
        if not _kernel32.OpenProcessToken(phandle, TOKEN_QUERY, thandle):
            raise ctypes.WinError()

        try:
            retlen = DWORD(0)
            if (
                _advapi32.GetTokenInformation(thandle, TokenUser, None, 0, ctypes.byref(retlen))
                or ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER
            ):
                raise ctypes.WinError()

            tuser_buf = (ctypes.c_char * retlen.value)()
            if not _advapi32.GetTokenInformation(
                thandle, TokenUser, ctypes.byref(tuser_buf), retlen.value, ctypes.byref(retlen)
            ):
                raise ctypes.WinError()
            tuser = TOKEN_USER.from_buffer(tuser_buf)

            namelen = DWORD(10)
            domlen = DWORD(10)
            nameuse = ctypes.c_int()
            while True:
                namebuf = (ctypes.c_wchar * namelen.value)()
                dombuf = (ctypes.c_wchar * domlen.value)()

                if _advapi32.LookupAccountSidW(
                    None,
                    tuser.User.Sid,
                    namebuf,
                    ctypes.byref(namelen),
                    dombuf,
                    ctypes.byref(domlen),
                    ctypes.byref(nameuse),
                ):
                    break
                else:
                    ex = ctypes.WinError()
                    if ex.winerror != ERROR_INSUFFICIENT_BUFFER:  # pylint: disable=no-member
                        raise ex

            return namebuf.value if nameuse.value == SidTypeUser else ""

        finally:
            _kernel32.CloseHandle(thandle)


def proc_num_handles(proc: "Process") -> int:
    try:
        with _pid_handle(proc.pid, PROCESS_QUERY_LIMITED_INFORMATION) as handle:
            count = DWORD()
            if _kernel32.GetProcessHandleCount(handle, ctypes.byref(count)):
                return count.value
            else:
                raise ctypes.WinError()

    except PermissionError:
        with _get_sysprocinfo(proc.pid) as (pinfo, _):
            return pinfo.HandleCount


def proc_open_files(proc: "Process") -> List[ProcessOpenFile]:
    with _pid_handle(proc.pid, PROCESS_DUP_HANDLE | SYNCHRONIZE) as proc_handle:
        _proc_check_alive(proc_handle)

        handles = []
        for hinfo in _list_handleinfos_ex():
            if hinfo.UniqueProcessId == proc.pid and (
                hinfo.GrantedAccess & (FILE_SHARE_READ | FILE_SHARE_WRITE)
            ):
                handles.append(hinfo.HandleValue)

        files = []
        for handle in handles:
            path = _get_handle_path(proc_handle, handle)
            if path is not None:
                if path.startswith("\\\\?\\"):
                    path = path[4:]
                files.append(ProcessOpenFile(path=path, fd=-1))

    return files


def _get_handle_path(proc_handle: HANDLE, src_handle: int) -> Optional[str]:
    file_handle = HANDLE()
    if not _kernel32.DuplicateHandle(
        proc_handle,
        src_handle,
        _kernel32.GetCurrentProcess(),
        ctypes.byref(file_handle),
        0,
        0,
        DUPLICATE_SAME_ACCESS,
    ):
        return None

    try:
        buf = (ctypes.c_wchar * (MAX_PATH + 1))()
        if not _kernel32.GetFinalPathNameByHandleW(file_handle, ctypes.byref(buf), len(buf), 0):
            return None

        return buf.value
    finally:
        _kernel32.CloseHandle(file_handle)


def proc_num_threads(proc: "Process") -> int:
    return _get_procentry(proc.pid).cntThreads


def proc_threads(proc: "Process") -> List[ThreadInfo]:
    with _get_sysprocinfo(proc.pid) as (_, tinfos):
        return [
            ThreadInfo(
                id=tinfo.tid,
                user_time=tinfo.UserTime / 10000000,
                system_time=tinfo.KernelTime / 10000000,
            )
            for tinfo in tinfos
        ]


def proc_suspend(proc: "Process") -> None:
    with _pid_handle(proc.pid, PROCESS_SUSPEND_RESUME) as handle:
        _handle_ntstatus_code(_ntdll.NtSuspendProcess(handle))


def proc_resume(proc: "Process") -> None:
    with _pid_handle(proc.pid, PROCESS_SUSPEND_RESUME) as handle:
        _handle_ntstatus_code(_ntdll.NtResumeProcess(handle))


def proc_getprioclass(proc: "Process") -> PriorityClass:
    with _pid_handle(proc.pid, PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE) as handle:
        _proc_check_alive(handle)
        priocls = _kernel32.GetPriorityClass(handle)
        if priocls == 0:
            raise ctypes.WinError()

    return PriorityClass(priocls)


def proc_setprioclass(proc: "Process", priocls: PriorityClass) -> None:
    with _pid_handle(proc.pid, PROCESS_SET_INFORMATION | SYNCHRONIZE) as handle:
        _proc_check_alive(handle)
        if not _kernel32.SetPriorityClass(handle, priocls.value):
            raise ctypes.WinError()


def pid_exists(pid: int) -> bool:
    if pid < 0:
        return False
    elif pid == 0:
        return True
    else:
        try:
            with _pid_handle(pid, PROCESS_QUERY_LIMITED_INFORMATION):
                pass
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        else:
            return True


def iter_pids() -> Iterator[int]:
    maxprocs = 500

    while True:
        procs = (DWORD * maxprocs)()
        needed = DWORD()

        if not _psapi.EnumProcesses(procs, len(procs) * DWORD_SIZE, ctypes.byref(needed)):
            raise ctypes.WinError()

        nprocs = needed.value // DWORD_SIZE

        if nprocs < maxprocs:
            return iter(sorted(procs[:nprocs]))

        # The array wasn't large enough; resize and try again
        maxprocs *= 2


def iter_pid_raw_create_time(
    *,
    skip_perm_error: bool = False,  # pylint: disable=unused-argument
    ppids: Optional[Set[int]] = None,
) -> Iterator[Tuple[int, float]]:
    return iter(
        sorted(
            (pinfo.pid, float(pinfo.CreateTime))
            for pinfo, _ in _iter_sysprocinfos()
            if ppids is None or pinfo.ppid in ppids
        )
    )


def _get_all_proc_times_pid(
    pid: int, *, check_alive: bool = False
) -> Tuple[FILETIME, FILETIME, FILETIME, FILETIME]:
    with _pid_handle(pid, PROCESS_QUERY_LIMITED_INFORMATION) as handle:
        if check_alive:
            _proc_check_alive(handle)

        t_creation = FILETIME()
        t_exit = FILETIME()
        t_kernel = FILETIME()
        t_user = FILETIME()

        if _kernel32.GetProcessTimes(
            handle,
            ctypes.byref(t_creation),
            ctypes.byref(t_exit),
            ctypes.byref(t_kernel),
            ctypes.byref(t_user),
        ):
            return t_creation, t_kernel, t_user, t_exit
        else:
            raise ctypes.WinError()


def _get_proc_times_pid(
    pid: int, *, check_alive: bool = False
) -> Tuple[FILETIME, FILETIME, FILETIME, FILETIME]:
    try:
        return _get_all_proc_times_pid(pid, check_alive=check_alive)[:3]
    except PermissionError:
        with _get_sysprocinfo(pid) as (pinfo, _):
            return (
                FILETIME.unpack(pinfo.CreateTime),
                FILETIME.unpack(pinfo.KernelTime),
                FILETIME.unpack(pinfo.UserTime),
            )


def pid_raw_create_time(pid: int) -> float:
    return _get_proc_times_pid(pid, check_alive=True)[0].pack()


def translate_create_time(raw_create_time: float) -> float:
    return FILETIME.unpack(raw_create_time).to_timestamp()


def proc_cpu_times(proc: "Process") -> ProcessCPUTimes:
    _, t_kernel, t_user = _get_proc_times_pid(proc.pid)

    return ProcessCPUTimes(
        user=t_user.pack() / 10000000,
        system=t_kernel.pack() / 10000000,
        children_user=0,
        children_system=0,
    )


def proc_cpu_getaffinity(proc: "Process") -> Set[int]:
    with _pid_handle(proc.pid, PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE) as handle:
        _proc_check_alive(handle)

        procmask = ULONG_PTR()
        sysmask = ULONG_PTR()
        if not _kernel32.GetProcessAffinityMask(
            handle, ctypes.byref(procmask), ctypes.byref(sysmask)
        ):
            raise ctypes.WinError()

    return set(_util.expand_bitmask(procmask.value, start=0))


def proc_cpu_setaffinity(proc: "Process", cpus: List[int]) -> None:
    mask = _util.pack_bitmask(cpus, start=0, end=8 * ctypes.sizeof(ULONG_PTR))
    with _pid_handle(
        proc.pid,
        PROCESS_SET_INFORMATION | (0 if mask else PROCESS_QUERY_LIMITED_INFORMATION) | SYNCHRONIZE,
    ) as handle:
        _proc_check_alive(handle)

        if not mask:
            # Empty CPU list; reset to the system mask
            procmask = ULONG_PTR()
            sysmask = ULONG_PTR()
            if not _kernel32.GetProcessAffinityMask(
                handle, ctypes.byref(procmask), ctypes.byref(sysmask)
            ):
                raise ctypes.WinError()
            mask = sysmask.value

        if not _kernel32.SetProcessAffinityMask(handle, mask):
            raise ctypes.WinError()


def proc_memory_info(proc: "Process") -> ProcessMemoryInfo:
    try:
        with _pid_handle(proc.pid, PROCESS_QUERY_LIMITED_INFORMATION) as handle:
            _proc_check_alive(handle)

            counts = PROCESS_MEMORY_COUNTERS_EX()
            if not _psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(counts), ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            ):
                raise ctypes.WinError()

            return ProcessMemoryInfo(
                num_page_faults=counts.PageFaultCount,
                peak_wset=counts.PeakWorkingSetSize,
                wset=counts.WorkingSetSize,
                peak_paged_pool=counts.QuotaPeakPagedPoolUsage,
                paged_pool=counts.QuotaPagedPoolUsage,
                peak_nonpaged_pool=counts.QuotaPeakNonPagedPoolUsage,
                nonpaged_pool=counts.QuotaNonPagedPoolUsage,
                pagefile=counts.PagefileUsage,
                peak_pagefile=counts.PeakPagefileUsage,
                private=counts.PrivateUsage,
            )

    except PermissionError:
        with _get_sysprocinfo(proc.pid) as (pinfo, _):
            return ProcessMemoryInfo(
                num_page_faults=pinfo.PageFaultCount,
                peak_wset=pinfo.PeakWorkingSetSize,
                wset=pinfo.WorkingSetSize,
                peak_paged_pool=pinfo.QuotaPeakPagedPoolUsage,
                paged_pool=pinfo.QuotaPagedPoolUsage,
                peak_nonpaged_pool=pinfo.QuotaPeakNonPagedPoolUsage,
                nonpaged_pool=pinfo.QuotaNonPagedPoolUsage,
                pagefile=pinfo.PagefileUsage,
                peak_pagefile=pinfo.PeakPagefileUsage,
                private=pinfo.PrivatePageCount,
            )


# def proc_memory_maps(proc: "Process") -> List[ProcessMemoryMap]:
#     with _pid_handle(
#         proc.pid, PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | SYNCHRONIZE
#     ) as proc_handle:
#         _proc_check_alive(proc_handle)

#         handles = []
#         for hinfo in _list_handleinfos_ex():
#             if hinfo.UniqueProcessId == proc.pid:
#                 print({field[0]: getattr(hinfo, field[0]) for field in hinfo._fields_})
#                 handles.append(hinfo.HandleValue)

#         results = []

#         modinfo = MODULEINFO()
#         pathbuf = (ctypes.c_wchar * (MAX_PATH + 1))()
#         for handle in handles:
#             # print({field[0]: getattr(modinfo, field[0]) for field in modinfo._fields_})
#             if not _psapi.GetMappedFileNameW(
#                 proc_handle, handle, pathbuf, ctypes.sizeof(pathbuf)
#             ):
#                 continue
#             print(pathbuf.value)
#             # TODO: This is broken

#             results.append(
#                 ProcessMemoryMap(
#                     path=pathbuf.value,
#                     addr_start=modinfo.lpBaseOfDll or 0,
#                     addr_end=(modinfo.lpBaseOfDll or 0) + modinfo.SizeOfImage,
#                     perms="",
#                     rss=modinfo.SizeOfImage,
#                 )
#             )

#         return results


# def group_memory_maps(maps: List[ProcessMemoryMap]) -> ProcessMemoryMapGrouped:
#     return ProcessMemoryMapGrouped(
#         path=maps[0].path,
#         rss=sum(mmap.rss for mmap in maps),
#     )


def proc_wait(proc: "Process", timeout: Union[int, float, None]) -> Optional[int]:
    try:
        with _pid_handle(proc.pid, PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE) as handle:
            if timeout is None:
                res = _kernel32.WaitForSingleObject(handle, INFINITE)
                if res != WAIT_OBJECT_0:
                    raise ctypes.WinError()

            else:
                timeout_ms = int(timeout * 1000)
                max_timeout_ms = 2**32 - 2
                while timeout_ms > max_timeout_ms:
                    res = _kernel32.WaitForSingleObject(handle, max_timeout_ms)
                    if res == WAIT_OBJECT_0:
                        break
                    elif res != WAIT_TIMEOUT:
                        raise ctypes.WinError()
                    timeout_ms -= max_timeout_ms

                else:
                    # We got WAIT_TIMEOUTs all the way through; check one last time with the
                    # remaining timeout
                    res = _kernel32.WaitForSingleObject(handle, timeout_ms)
                    if res == WAIT_TIMEOUT:
                        # Really timed out
                        raise TimeoutExpired(timeout, proc.pid)
                    elif res != WAIT_OBJECT_0:
                        raise ctypes.WinError()

            # If we got here, the process is dead
            code = DWORD()
            if not _kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                raise ctypes.WinError()
            return None if code.value == STILL_ACTIVE else code.value

    except ProcessLookupError:
        return None


def wait_procs(
    orig_procs: Iterable["Process"],
    timeout: Union[int, float, None],
    callback: Callable[["Process", Optional[int]], None],
) -> None:
    with contextlib.ExitStack() as stack:
        procs = []
        handles = []
        for proc in orig_procs:
            try:
                handle = stack.enter_context(
                    _pid_handle(proc.pid, PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE)
                )
            except ProcessLookupError:
                callback(proc, None)
            else:
                procs.append(proc)
                handles.append(handle)

        if not procs:
            return

        start_time = time.monotonic() if timeout is not None and timeout > 0 else 0
        cur_timeout_ms = int(max(timeout, 0) * 1000) if timeout is not None else INFINITE
        while True:
            res = _kernel32.WaitForMultipleObjects(
                len(handles), (HANDLE * len(handles))(*handles), 0, cur_timeout_ms
            )
            if res == WAIT_TIMEOUT:
                return
            elif res >= WAIT_OBJECT_0 and res < WAIT_OBJECT_0 + len(handles):
                i = res - WAIT_OBJECT_0
                code = DWORD()
                if not _kernel32.GetExitCodeProcess(handles[i], ctypes.byref(code)):
                    raise ctypes.WinError()
                callback(procs[i], code.value)
                del procs[i]
                del handles[i]
                if not procs:
                    return
            else:
                raise ctypes.WinError()

            if timeout is not None:
                if timeout > 0:
                    cur_timeout_ms = max(
                        min(int(((start_time + timeout) - time.monotonic()) * 1000), 2**32 - 2), 0
                    )
                else:
                    cur_timeout_ms = 0


wait_procs.max_procs = MAXIMUM_WAIT_OBJECTS


def _get_memstatus_ex() -> MEMORYSTATUSEX:
    buf = MEMORYSTATUSEX(dwLength=ctypes.sizeof(MEMORYSTATUSEX))
    if not _kernel32.GlobalMemoryStatusEx(ctypes.byref(buf)):
        raise ctypes.WinError()
    return buf


def _get_perfinfo() -> PERFORMANCE_INFORMATION:
    buf = PERFORMANCE_INFORMATION()
    if not _psapi.GetPerformanceInfo(ctypes.byref(buf), ctypes.sizeof(PERFORMANCE_INFORMATION)):
        raise ctypes.WinError()
    return buf


def virtual_memory() -> VirtualMemoryInfo:
    memstatus = _get_memstatus_ex()

    return VirtualMemoryInfo(
        total=memstatus.ullTotalPhys,
        available=memstatus.ullAvailPhys,
        free=memstatus.ullAvailPhys,
        used=memstatus.ullTotalPhys - memstatus.ullAvailPhys,
    )


def swap_memory() -> _util.SwapInfo:
    perfinfo = _get_perfinfo()

    return _util.SwapInfo(
        total=perfinfo.CommitLimit * perfinfo.PageSize,
        used=perfinfo.CommitTotal * perfinfo.PageSize,
        sin=0,
        sout=0,
    )


def physical_cpu_count() -> Optional[int]:
    # Call it once to get the size
    reqsize = DWORD(0)
    if (
        _kernel32.GetLogicalProcessorInformationEx(
            RelationProcessorCore, None, ctypes.byref(reqsize)
        )
        or ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER
    ):
        # This *should* have failed with ERROR_INSUFFICIENT_BUFFER
        return None

    # Then call it again to actually get the information
    buf = (ctypes.c_char * reqsize.value)()
    bufsize = DWORD(len(buf))
    if not _kernel32.GetLogicalProcessorInformationEx(
        RelationProcessorCore, buf, ctypes.byref(bufsize)
    ):
        # Something's wrong
        return None

    return (
        sum(
            lpinfo.Relationship == RelationProcessorCore
            for lpinfo in _util.iter_packed_structures(
                buf.raw[: bufsize.value], SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX, "Size"
            )
        )
        or None
    )


def percpu_freq() -> List[Tuple[float, float, float]]:
    ncpus = os.cpu_count()
    assert ncpus

    buf = (PROCESSOR_POWER_INFORMATION * ncpus)()
    _handle_ntstatus_code(
        _powrprof.CallNtPowerInformation(ProcessorInformation, None, 0, buf, ctypes.sizeof(buf))
    )

    return [(float(pinfo.CurrentMhz), 0.0, float(pinfo.MaxMhz)) for pinfo in buf]


def disk_usage(path: Union[str, bytes, "os.PathLike[str]", "os.PathLike[bytes]"]) -> DiskUsage:
    vfs_stat = os.statvfs(os.fspath(path))

    total = vfs_stat.f_blocks * vfs_stat.f_frsize
    free = vfs_stat.f_bavail * vfs_stat.f_frsize
    used = total - vfs_stat.f_bfree * vfs_stat.f_frsize

    return DiskUsage(total=total, free=free, used=used)


def sensors_power() -> PowerSupplySensorInfo:
    batteries = []

    devhandle = _setupapi.SetupDiGetClassDevsW(
        ctypes.byref(GUID_DEVCLASS_BATTERY), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    )
    if devhandle != INVALID_HANDLE_VALUE:
        try:
            for i in range(100):
                idata = SP_DEVICE_INTERFACE_DATA()
                idata.cbSize = ctypes.sizeof(idata)
                if not _setupapi.SetupDiEnumDeviceInterfaces(
                    devhandle,
                    None,
                    ctypes.byref(GUID_DEVCLASS_BATTERY),
                    i,
                    ctypes.byref(idata),
                ):
                    if ctypes.GetLastError() == ERROR_NO_MORE_ITEMS:
                        break
                    else:
                        continue

                detailbuf = (
                    ctypes.c_char * (ctypes.sizeof(SP_DEVICE_INTERFACE_DETAIL_DATA_A) + MAX_PATH)
                )()
                detail = SP_DEVICE_INTERFACE_DETAIL_DATA_A.from_buffer(detailbuf)
                detail.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DETAIL_DATA_A)
                if not _setupapi.SetupDiGetDeviceInterfaceDetailA(
                    devhandle, ctypes.byref(idata), ctypes.byref(detail), len(detailbuf), None, None
                ):
                    continue

                batpath = ctypes.string_at(ctypes.addressof(detail.DevicePath))

                bathandle = _kernel32.CreateFileA(
                    batpath, GENERIC_READ, FILE_SHARE_READ, None, OPEN_EXISTING, 0, None
                )
                if bathandle == INVALID_HANDLE_VALUE:
                    continue

                try:
                    nbytes = DWORD()

                    battag = ULONG()
                    if not _kernel32.DeviceIoControl(
                        bathandle,
                        IOCTL_BATTERY_QUERY_TAG,
                        ctypes.byref(ULONG(0)),
                        ctypes.sizeof(ULONG),
                        ctypes.byref(battag),
                        ctypes.sizeof(ULONG),
                        ctypes.byref(nbytes),
                        None,
                    ):
                        continue

                    batwaitstatus = BATTERY_WAIT_STATUS()
                    batstatus = BATTERY_STATUS()
                    batwaitstatus.Timeout = 0
                    batwaitstatus.BatteryTag = battag
                    if not _kernel32.DeviceIoControl(
                        bathandle,
                        IOCTL_BATTERY_QUERY_STATUS,
                        ctypes.byref(batwaitstatus),
                        ctypes.sizeof(batwaitstatus),
                        ctypes.byref(batstatus),
                        ctypes.sizeof(batstatus),
                        ctypes.byref(nbytes),
                        None,
                    ):
                        continue

                    batqueryinfo = BATTERY_QUERY_INFORMATION()
                    batqueryinfo.BatteryTag = battag

                    batnamebuf = (ctypes.c_wchar * 100)()
                    batqueryinfo.InformationLevel = BatteryDeviceName
                    if _kernel32.DeviceIoControl(
                        bathandle,
                        IOCTL_BATTERY_QUERY_INFORMATION,
                        ctypes.byref(batqueryinfo),
                        ctypes.sizeof(batqueryinfo),
                        ctypes.byref(batnamebuf),
                        ctypes.sizeof(batnamebuf),
                        ctypes.byref(nbytes),
                        None,
                    ):
                        name = batnamebuf.value[: nbytes.value]
                    else:
                        name = f"BAT{i}"

                    batinfo = BATTERY_INFORMATION()
                    batqueryinfo.InformationLevel = BatteryInformation
                    if not _kernel32.DeviceIoControl(
                        bathandle,
                        IOCTL_BATTERY_QUERY_INFORMATION,
                        ctypes.byref(batqueryinfo),
                        ctypes.sizeof(batqueryinfo),
                        ctypes.byref(batinfo),
                        ctypes.sizeof(batinfo),
                        ctypes.byref(nbytes),
                        None,
                    ):
                        continue

                    rawtemp = ULONG()
                    batqueryinfo.InformationLevel = BatteryTemperature
                    if not _kernel32.DeviceIoControl(
                        bathandle,
                        IOCTL_BATTERY_QUERY_INFORMATION,
                        ctypes.byref(batqueryinfo),
                        ctypes.sizeof(batqueryinfo),
                        ctypes.byref(rawtemp),
                        ctypes.sizeof(rawtemp),
                        ctypes.byref(nbytes),
                        None,
                    ):
                        # Failure; ignore
                        rawtemp.value = 0

                    if batstatus.Capacity == BATTERY_UNKNOWN_CAPACITY:
                        continue

                    percent = batstatus.Capacity * 100 / batinfo.FullChargedCapacity

                    if batstatus.PowerState & BATTERY_CHARGING:
                        status = BatteryStatus.CHARGING
                    elif batstatus.PowerState & BATTERY_DISCHARGING:
                        status = BatteryStatus.DISCHARGING
                    elif percent >= 100:
                        status = BatteryStatus.FULL
                    else:
                        status = BatteryStatus.UNKNOWN

                    secsleft = None
                    secsleft_full = None
                    if batinfo.Capabilities & BATTERY_CAPACITY_RELATIVE:
                        energy_full = None
                        # energy_full_design = None
                        energy_now = None
                        power_now = None

                        if batstatus.Rate != BATTERY_UNKNOWN_RATE:
                            if batstatus.PowerState & BATTERY_DISCHARGING and batstatus.Rate < 0:
                                secsleft = (
                                    (batinfo.FullChargedCapacity - batstatus.Capacity)
                                    * 3600
                                    / (-batstatus.Rate)
                                )
                            elif batstatus.PowerState & BATTERY_CHARGING and batstatus.Rate > 0:
                                secsleft_full = batstatus.Capacity * 3600 / batstatus.Rate

                    else:
                        energy_full = batinfo.FullChargedCapacity * 1000
                        # energy_full_design = batinfo.DesignedCapacity * 1000
                        energy_now = batstatus.Capacity * 1000
                        power_now = (
                            abs(batstatus.Rate) * 1000
                            if batstatus.Rate != BATTERY_UNKNOWN_RATE
                            else None
                        )

                    temperature = None
                    if rawtemp.value:
                        temperature = rawtemp.value / 10.0 - 273.15

                finally:
                    _kernel32.CloseHandle(bathandle)

                batteries.append(
                    BatteryInfo(
                        name=name,
                        status=status,
                        percent=percent,
                        energy_full=energy_full,
                        # energy_full_design=energy_full_design,
                        energy_now=energy_now,
                        power_now=power_now,
                        temperature=temperature,
                        _secsleft=secsleft,
                        _secsleft_full=secsleft_full,
                    )
                )

        finally:
            _setupapi.SetupDiDestroyDeviceInfoList(devhandle)

    has_ac_power = sensors_is_on_ac_power()
    return PowerSupplySensorInfo(
        batteries=batteries,
        ac_supplies=[ACPowerInfo(name="AC", is_online=has_ac_power)]
        if has_ac_power is not None
        else [],
    )


def sensors_is_on_ac_power() -> Optional[bool]:
    powstatus = SYSTEM_POWER_STATUS()
    if not _kernel32.GetSystemPowerStatus(ctypes.byref(powstatus)):
        return None

    return {0: False, 1: True}.get(powstatus.ACLineStatus)


def sensors_battery_total_alt(_: Optional[bool]) -> Optional[BatteryInfo]:
    powstatus = SYSTEM_POWER_STATUS()
    if not _kernel32.GetSystemPowerStatus(ctypes.byref(powstatus)):
        return None

    if (
        powstatus.BatteryFlag == 128
        or powstatus.BatteryLifePercent < 0
        or powstatus.BatteryLifePercent > 100
    ):
        return None

    if powstatus.ACLineStatus == 0:
        power_plugged = False
    elif powstatus.ACLineStatus == 1:
        power_plugged = True
    else:
        power_plugged = None

    if powstatus.BatteryFlag & 8:
        status = BatteryStatus.CHARGING
    elif power_plugged is False:
        status = BatteryStatus.DISCHARGING
    elif power_plugged and powstatus.BatteryLifePercent == 100:
        status = BatteryStatus.FULL
    else:
        status = BatteryStatus.UNKNOWN

    secsleft = None
    if status == BatteryStatus.DISCHARGING and powstatus.BatteryLifeTime != DWORD(-1).value:
        secsleft = powstatus.BatteryLifeTime

    return BatteryInfo(
        name="Combined",
        status=status,
        percent=float(powstatus.BatteryLifePercent),
        energy_full=None,
        energy_now=None,
        power_now=None,
        _power_plugged=power_plugged,
        _secsleft=secsleft,
    )


def boot_time() -> float:
    # Round the result to reduce small variations
    return round(time.time() - time_since_boot(), 1)


def time_since_boot() -> float:
    return cast(float, _kernel32.GetTickCount64() / 1000.0)


def uptime() -> float:
    res = ctypes.c_ulonglong()
    if _kernel32.QueryUnbiasedInterruptTime(ctypes.byref(res)):
        return res.value / 10000000.0
    else:
        raise ctypes.WinError()
