#ifndef SCCD_STRUCT_H
#define SCCD_STRUCT_H

/*
 * sccd_struct.h
 *
 * AUTOGENERATED FILE! ONLY EDIT IF YOU ARE A MACHINE!
 *
 * Created on: 2020-06-30 19:18:25.783891
 * Author: Dephy, Inc.
 *
 */

#include "SCCD_device_spec.h"
#include <stdio.h>
#include <time.h>
#include <string.h>
#include <stdint.h>

#include <stdbool.h>

#define SCCD_SYSTEM_TIME_POS 24
#define SCCD_STRUCT_DEVICE_FIELD_COUNT 25
#define SCCD_LABEL_MAX_CHAR_LENGTH 14

//This is The Device fields*10 + deviceField+1. Ten is the max string length of 2^32 in decimal separated from commas
#define SCCD_DATA_STRING_LENGTH 276

#ifdef __cplusplus
extern "C"
{
#endif

#pragma pack(1)

struct SCCDState
{
	int prototype;
	int id;
	int state_time;
	int cells_0_mv;
	int cells_0_mah;
	int cells_1_mv;
	int cells_1_mah;
	int cells_2_mv;
	int cells_2_mah;
	int cells_3_mv;
	int cells_3_mah;
	int cells_4_mv;
	int cells_4_mah;
	int cells_5_mv;
	int cells_5_mah;
	int cells_6_mv;
	int cells_6_mah;
	int cells_7_mv;
	int cells_7_mah;
	int cells_8_mv;
	int cells_8_mah;
	int cellcharge;
	int celldischarge;
	int status;

	//the system time
	int systemTime;
};

#pragma pack()

/// \brief Assigns the data in the buffer to the correct struct parameters
///
///@param SCCD is the struct with the data to be set
///
///@param _deviceStateBuffer is the buffer containing the data to be assigned to the struct
///
///@param systemStartTime the time the system started. If unknown, use 0.
///
void SCCDSetData(struct SCCDState *sccd, uint32_t _deviceStateBuffer[], int systemStartTime);

/// \brief takes all data and places it into single, comma separated string
///
///@param SCCD is the struct with the data to be placed in the string
///
///@param dataString is where the new string wll be placed
///
void SCCDDataToString(struct SCCDState *sccd, char dataString[SCCD_DATA_STRING_LENGTH]);

/// \brief retrieves the string equivalent of all parameter names
///
///@param labels is the array of labels containing the parameter names
///
void SCCDGetLabels(char labels[SCCD_STRUCT_DEVICE_FIELD_COUNT][SCCD_LABEL_MAX_CHAR_LENGTH]);

/// \brief retrieves the string equivalent of parameter names starting with state time.  Parameters
/// prior to state time, such as id,  are not included.
///
///@param labels is the array of labels containing the parameter names
///
int SCCDGetLabelsForLog(char labels[SCCD_STRUCT_DEVICE_FIELD_COUNT][SCCD_LABEL_MAX_CHAR_LENGTH]);

/// \brief Places data from struct into an array.
///
///@param actpack the data to be converte to an array
///
///@param actpackDataArray the array in which to place the data
///
void SCCDStructToDataArray(struct SCCDState sccd, int32_t sccdDataArray[SCCD_STRUCT_DEVICE_FIELD_COUNT]);

/// \brief Get data based on data position from device communication.
///
///@param actpack the data to access
///
///@param dataPosition the position of data to access
///
///@param dataValid return false if requested data position is invalid
///
int GetSCCDDataByDataPosition( struct SCCDState sccd, int dataPosition);

#ifdef __cplusplus
}//extern "C"
#endif

#endif ////ACTPACK_STRUCT_H
