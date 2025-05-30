# PerfTools/AllocMonitor Description

## Introduction

This package works with the PerfTools/AllocMonitorPreload package to provide a general facility to watch allocations and deallocations.
This is accomplished by using LD_PRELOAD with libPerfToolsAllocMonitorPreload.so and registering a class inheriting from `AllocMonotorBase`
with `AllocMonitorRegistry`. The preloaded library puts in proxies for the C and C++ allocation methods (and forwards the calls to the
original job methods). These proxies communicate with `AllocMonitorRegistry` which, in turn, call methods of the registered monitors.

## Extending

To add a new monitor, one inherits from `cms::perftools::AllocMonitorBase` and overrides the `allocCalled` and
`deallocCalled` methods.

- `AllocMonitorBase::allocCalled(size_t iRequestedSize, size_t iActualSize)` : `iRequestedSize` is the number of bytes being requested by the allocation call. `iActualSize` is the actual number of bytes returned by the allocator. These can be different because of alignment constraints (e.g. asking for 1 byte but all allocations must be aligned on a particular memory boundary) or internal details of the allocator.

- `AllocMonitorBase::deallocCalled(size_t iActualSize)` : `iActualSize` is the actual size returned when the associated allocation was made. NOTE: the glibc extended interface does not provide a way to find the requested size base on the address returned from an allocation, it only provides the actual size.

When implementing `allocCalled` and `deallocCalled` it is perfectly fine to do allocations/deallocations. The facility
guarantees that those internal allocations will not cause any callbacks to be send to any active monitors.


To add a monitor to the facility, one must access the registry by calling the static method
`cms::perftools::AllocMonitorRegistry::instance()` and then call the member function
`T* createAndRegisterMonitor(ARGS&&... iArgs)`. The function will internally create a monitor of type `T` (being careful
to not cause callbacks during the allocation) and pass the arguments `iArgs` to the constructor.

The monitor is owned by the registry and should not be deleted by any other code. If one needs to control the lifetime
of the monitor, one can call `cms::perftools::AllocMonitorRegistry::deregisterMonitor` to have the monitor removed from
the callback list and be deleted (again, without the deallocation causing any callbacks).

NOTE: Experience has shown that using thread_local within a call to `allocCalled` or `deallocCalled` can lead to unexpected behavior. Therefore if per thread information must be gathered it is recommended to make a system that uses thread ids.
An example of such code can be found in the implementation of ModuleAllocMonitor.

## General usage

To use the facility, one needs to use LD_PRELOAD to load in the memory proxies before the application runs, e.g.
```
LD_PRELOAD=libPerfToolsAllocMonitorPreload.so cmsRun some_config_cfg.py
```

Internally, the program needs to register a monitor with the facility. When using `cmsRun` this can most easily be done
by loading a Service which setups a monitor. If one fails to do the LD_PRELOAD, then when the monitor is registered, the
facility will throw an exception.

It is also possible to use LD_PRELOAD to load another library which auto registers a monitor even before the program
begins. See [PerfTools/MaxMemoryPreload](../MaxMemoryPreload/README.md) for an example.

## Services

### SimpleAllocMonitor
This service registers a monitor when the service is created (after python parsing is finished but before any modules
have been loaded into cmsRun) and reports its accumulated information when the service is destroyed (services are the
last plugins to be destroyed by cmsRun). The monitor reports
- Total amount of bytes requested by all allocation calls
- The maximum amount of _used_ (i.e actual size) allocated memory that was in use by the job at one time.
- Number of calls made to allocation functions while the monitor was running.
- Number of calls made to deallocation functions while the monitor was running.

This service is multi-thread safe. Note that when run multi-threaded the maximum reported value will vary from job to job.


### EventProcessingAllocMonitor
This service registers a monitor at the end of beginJob (after all modules have been loaded and setup) and reports its accumulated information at the beginning of endJob (after the event loop has finished but before any cleanup is done). This can be useful in understanding how memory is being used during the event loop. The monitor reports
- Total amount of bytes requested by all allocation calls during the event loop
- The maximum amount of _used_ (i.e. actual size) allocated memory that was in use in the event loop at one time.
- The amount of _used_ memory allocated during the loop that has yet to be reclaimed by calling deallocation.
- Number of calls made to allocation functions during the event loop.
- Number of calls made to deallocation functions during the event loop.

This service is multi-thread safe. Note that when run multi-threaded the maximum reported value will vary from job to job.

### HistogrammingAllocMonitor
This service registers a monitor when the service is created (after python parsing is finished but before any modules
have been loaded into cmsRun) and reports its accumulated information when the service is destroyed (services are the
last plugins to be destroyed by cmsRun). The monitor histograms the values into bins of number of bytes where each
bin is a power of 2 larger than the previous. The histograms made are
- Amount of bytes requested by all allocation calls
- Amount of bytes actually used by all allocation calls
- Amount of bytes actually returned by all deallocation calls

This service is multi-thread safe. Note that when run multi-threaded the maximum reported value will vary from job to job.

### PeriodicAllocMonitor
This service registers a monitor when the service is created (after python parsing is finished but before any modules
have been loaded into cmsRun) and prints its accumulated information to the specified file at specified intervals. Both
the file name and  interval are specified by setting parameters of the service in the configuration. The parameters are
- `filename`: name of file to which to write reports
- `millisecondsPerMeasurement`: number of milliseconds to wait between making each report

The output file contains the following information on each line
- The time, in milliseconds, since the service was created
- The total number of Runs which have been started in the job
- The total number of LuminosityBlocks which have been started
- The total number of Events which have been started
- The total number of Events which have finished
- Total amount of bytes requested by all allocation calls since the service started
- The maximum amount of _used_ (i.e. actual size) allocated memory that has been seen up to this point in the job
- The amount of _used_ memory allocated at the time the report was made.
- The largest single allocation request that has been seen up to the time of the report
- Number of calls made to allocation functions
- Number of calls made to deallocation functions

This service is multi-thread safe. Note that when run multi-threaded the maximum reported value will vary from job to job.

### ModuleAllocMonitor
This service registers a monitor when the service is created (after python parsing is finished but before any modules
have been loaded into cmsRun) and writes module related information to the specified file. The file name, an optional
list of module names, and  an optional number of initial events to skip are specified by setting parameters of the
service in the configuration. The parameters are
- `filename`: name of file to which to write reports
- `moduleNames`: list of modules which should have their information added to the file. An empty list specifies all modules should be included.
- `nEventsToSkip`: the number of initial events that must be processed before reporting happens.

The beginning of the file contains a description of the structure and contents of the file.

This service is multi-thread safe.


### ModuleEventAllocMonitor
This service registers a monitor when the service is created (after python parsing is finished but before any modules
have been loaded into cmsRun) and writes event based module related information to the specified file. The service
keeps track of the address of each allocation requested during an event from each module and pairs them with any
deallocation using the same address. The list of addresses are kept until the event data products are deleted at which
time the dallocations are paired with allocations done in a module. The list of addresses are then cleared (to keep memory usage down) but the amount of unassociated deallocations for each module is recorded per event.
The file name, an optional list of module names, and  an optional number of initial events to skip are specified by setting parameters of the
service in the configuration. The parameters are
- `filename`: name of file to which to write reports
- `moduleNames`: list of modules which should have their information added to the file. An empty list specifies all modules should be included.
- `nEventsToSkip`: the number of initial events that must be processed before reporting happens.

The beginning of the file contains a description of the structure and contents of the file. The file can be analyzed with the helper script `edmModuleEventAllocMonitorAnalyze.py`. The script can be used to find modules where the memory is being retained between Events as well as modules where the memory appears to be growing Event to Event. Use `--help` with the script for a full description.

This service is multi-thread safe.


### IntrusiveAllocMonitor

This service registers a monitor when the service is created (after python parsing is finished, but before any modules have been loaded into cmsRun). The user can then start the monitoring in their code as shown in the example below. The monitoring stops, in an RAII fashion, at the end of the scope and the results of the memory operations are printed with the [MessageLogger](../../FWCore/MessageService/Readme.md) with an `IntrusiveAllocMonitor` message category.

```cpp
#include "FWCore/AbstractServices/interface/IntrusiveMonitorBase.h"
#include "FWCore/ServiceRegistry/interface/Service.h"


void someFunction() {
  {
    edm::Service<IntrusiveMonitorBase> monitor;
    auto guard = monitor.startMeasurement("Measurement description");

    // more code doing memory allocations
  }
}

```

The message will print
| Field | Description |
|-------|-------------|
| `requested` | Total number of requested bytes |
| `added ` | Total number of bytes added (can be more than `requested`) |
| `max alloc` | Largest single memory allocation |
| `peak` | Maximum amount of allocated memory at any given moment |
| `nAlloc` | Number of memory allocations |
| `nDealloc` | Number of memory deallocations |

This service is multi-thread safe, and concurrent measurements can be done in different threads. Nested measurements are not supported (i.e. one thread can be doing only one measurement at a time), and neither are measurements started in one thread and ended in different thread.