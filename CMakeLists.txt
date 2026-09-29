cmake_minimum_required(VERSION 3.5 FATAL_ERROR)

project(Simulation)

file(COPY ${PROJECT_SOURCE_DIR}/macros DESTINATION ${PROJECT_BINARY_DIR})
file(COPY ${PROJECT_SOURCE_DIR}/geometry DESTINATION ${PROJECT_BINARY_DIR})
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/output )

find_package(Geant4 REQUIRED ui_all vis_all)

include(${Geant4_USE_FILE})
file(GLOB sources ${PROJECT_SOURCE_DIR}/src/*.cc)
file(GLOB headers ${PROJECT_SOURCE_DIR}/include/*.hh)
include_directories(${PROJECT_SOURCE_DIR}/include)

add_executable(sim sim.cc ${sources} ${headers})

add_library(libCRY STATIC IMPORTED)
set_target_properties(libCRY PROPERTIES IMPORTED_LOCATION "${PROJECT_SOURCE_DIR}/cry_v1.7/lib/libCRY.a")
set_target_properties(libCRY PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${PROJECT_SOURCE_DIR}/cry_v1.7/src")


option(ADD_RADIOACTIVE "Add the Thorium box in the simulation option" OFF)
if (ADD_RADIOACTIVE)
	add_compile_definitions(ADD_RADIOACTIVE)
endif()

option(ADD_BACKGROUND_GPS "Use GPS gamma source for measured David lab background spectrum" OFF)
if (ADD_BACKGROUND_GPS)
	if (ADD_RADIOACTIVE)
		message(FATAL_ERROR "ADD_BACKGROUND_GPS and ADD_RADIOACTIVE cannot both be ON")
	endif()
	add_compile_definitions(ADD_BACKGROUND_GPS)
endif()

option(ADD_CRY_BACKGROUND_GPS "Use CRY muons and GPS measured gamma background in the same event" OFF)
if (ADD_CRY_BACKGROUND_GPS)
	if (ADD_RADIOACTIVE OR ADD_BACKGROUND_GPS)
		message(FATAL_ERROR "ADD_CRY_BACKGROUND_GPS cannot be combined with ADD_RADIOACTIVE or ADD_BACKGROUND_GPS")
	endif()
	add_compile_definitions(ADD_CRY_BACKGROUND_GPS)
	add_compile_definitions(ADD_SOURCE_TAGGING)
endif()

option(ADD_SCAN "Use a one-run muon scan source with per-event source truth" OFF)
if (ADD_SCAN)
	if (ADD_RADIOACTIVE OR ADD_BACKGROUND_GPS OR ADD_CRY_BACKGROUND_GPS)
		message(FATAL_ERROR "ADD_SCAN cannot be combined with ADD_RADIOACTIVE, ADD_BACKGROUND_GPS, or ADD_CRY_BACKGROUND_GPS")
	endif()
	add_compile_definitions(ADD_SCAN)
endif()

option(FILTER_FOR_TES "Do not record events that do not contain a TES hit" OFF)
if (FILTER_FOR_TES)
	add_compile_definitions(FILTER_FOR_TES)
endif()

option(ENABLE_MPI "Compile for Multiprocessing using MPI" OFF)
if (ENABLE_MPI)

# Set the compiler flag to MPI in the code
add_compile_definitions(MPI_ENABLE)

# Try and steal it form an environment variable first
set(G4mpi_DIR $ENV{G4MPI_DIR})

# Find the G4mpi package
find_package(G4mpi REQUIRED)

# Flag for using native mpi
add_definitions(-DTOOLS_USE_NATIVE_MPI) 

# Include mpi directories
include_directories(${G4mpi_INCLUDE_DIR})

target_link_libraries(sim ${Geant4_LIBRARIES} ${G4mpi_LIBRARIES} libCRY)

else()

target_link_libraries(sim ${Geant4_LIBRARIES} libCRY)

endif()


add_custom_target(Simulation DEPENDS sim)
