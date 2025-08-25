**Inhouse Development for EOL Application	20-8-2025**
PREPARED BY
SRI SAKTHIVEL R	

Table of Contents

S.NO	CONTENT	PAGE NO
1	INTRODUCTION	4
2	OPERATION	4
2.1	U666/N603 TEST SEQUENCE	4
2.1.1	PRESENCE	4
2.1.2	VERSION	4
2.1.3	VOLTAGE	5
2.1.4	VEHICLE ID	5
2.1.5	PHASE ANGLE OFFSET	5
2.2	IQube ST TEST SEQUENCE	6
2.2.1	API CALL	6
2.2.2	WRITE_TPMS_FRONT	6
2.2.3	WRITE_TPMS_REAR	6
2.3	Execution Steps	7
2.3.1	Initiate Process	7
2.3.2	Monitor Progress	7
2.3.3	Test Completion	8
2.3.4	Reset Process 	10
3	Track And Trace	11
4	Log Validation	12
4.1	File Location	12
4.2	File Structure	12
4.2.1	IQube ST Logs	12
4.2.2	U666/N603 Logs	12
4.3	Overview Of Logs	13
4.3.1	Header Information	13
4.3.2	Test Sequences	14
4.3.3	Cycle Time Summary	14
4.4	Auto Deletion of Logs	15
5	Software Updates	15
5.1	TVS NIRIX V1.1	15
5.2	TVS NIRIX V1.2	15
5.3	TVS NIRIX V1.4	15

















1. INTRODUCTION
TVS NIRIX is a flexible desktop program designed specifically for automotive manufacturing facilities, with an emphasis on diagnostic validation and car component certification. The application, written in Python and including a PyQt5 graphical interface, simplifies VIN-based testing workflows by allowing for seamless interaction with barcode scanners, APIs, and Excel-driven test sequences. 
It enables CAN bus connectivity for in-depth diagnostics and is designed to perform specialised tasks like TPMS parameter validation. The program interacts with the cluster ECU to automate sensor matching by getting MAC IDs via API, publishing them, and verifying successful pairing—all while logging actions locally for complete traceability. 
2. OPERATION
2.1	U666/N603 TEST SEQUENCE:
2.1.1	PRESENCE:
	Purpose: Checks the ECU presence in that vehicle where the pcan and scanners are connected.
	Input: Tx_can_id (request_id).
	Output: Rx_Hex_id (Response id) Returns True if the presence detected, False otherwise.
	Duration: Approximately 1-5 second.
	Success: Test Sequence is Presented (Passed).
	Failure: Issue in the Vehicle or PCAN.
2.1.2	VERSION:
	Purpose: Checks the ECU version in that vehicle where the pcan and scanners are connected.
	Input: Tx_can_id (request_id).
	Output: Rx_Hex_id (Response id), Returns True if the version detected, False otherwise.
	Duration: Approximately 1-5 second.
	Success: Returns the version to the main program if it gets the response id.
	Failure: Issue in the Vehicle or PCAN.

2.1.3	VOLTAGE:
	Purpose: Checks the Battery Voltage in that vehicle where the pcan and scanners are connected. Here there is lsl and usl limits, if the vehicle voltage is within these limits, then it will pass or else it fails.
	Input: Tx_Can_ID.
	Output: Rx_Hex_Id, Rx_Dec_ID, Voltage, Returns True if the Voltage detected, False.
	Duration: Approximately 1-5 second.
	Success: Returns the voltage to the main program if it gets the response id.
	Failure: Issue in the Vehicle or PCAN.
2.1.4	VEHICLE ID:
	Purpose: Matches the result for the VIN number in the api_vehicle_ID and the vehicle_ID for that vehicle.
	Input: VIN Number, Tx_Can_ID.
	Output: Returns True if the vehicle id matches the API vehicle id, False otherwise.
	Duration: Approximately 1-5 second.
	Success: Returns the actual vehicle id and true if it matches
	Failure: Vehicle id does not match with the API vehicle id or issue in the vehicle.
2.1.5	PHASE ANGLE OFFSET:
	Purpose: Matches the result for the VIN number in the api_phase_offset and the phase_angle_offset for that vehicle.
	Input: VIN Number, Tx_Can_ID.
	Output: Returns True if the vehicle phase angle matches the API phase angle, False otherwise.
	Duration: Approximately 1-5 seconds.
	Success:  Returns the actual vehicle phase angle and true if it matches.
	Failure: Vehicle Phase angle does not match with the API vehicle phase angle or issue in the vehicle.

2.2	IQube ST TEST SEQUENCE:
2.2.1 API CALL
	Purpose: Initiates an API request to retrieve TPMS parameters (e.g., front and rear MAC addresses) for the entered VIN.
	Input: VIN number.
	Output: Sets front_mac and rear_mac variables if successful; otherwise, returns False.
	Duration: Approximately 1 second (with a 1-second delay between tests).
	Success: Valid MAC addresses are retrieved and stored.
	Failure: Occurs if the API (http://10.121.2.107:3000/vehicles/processParams/VIN ) is 
unreachable or returns an error.
2.2.2 WRITE_TPMS_FRONT
	Purpose: Writes the front wheel MAC address to the TPMS system.
	Input: front_mac retrieved from API_CALL.
	Output: Returns True if the write operation succeeds, False otherwise.
	Duration: Approximately 1 second.
	Success: The TPMS system acknowledges the write operation.
	Failure: Occurs if front_mac is invalid or the write operation fails (e.g., communication error with TPMS hardware).
2.2.3 WRITE_TPMS_REAR
	Purpose: Writes the rear wheel MAC address to the TPMS system.
	Input: rear_mac retrieved from API_CALL.
	Output: Returns True if the write operation succeeds, False otherwise.
	Duration: Approximately 1 second.
	Success: The TPMS system acknowledges the write operation. 
	Failure: Occurs if rear_mac is invalid or the write operation fails.


2.3 Execution Steps
2.3.1 Initiate Process:
	Manually type a 17-character VIN starting with "MD6" (e.g., "MD612345678912345") in the "Enter VIN Number" field or use the scanner (Section 7) to input the VIN automatically.

                                    
2.3.2 Monitor Progress:
	You have selected PRD mode. Please ensure that the scanned or entered VIN and the selected active library (3W_Diagnostics, TPMS, or IVCU) are registered under PRD configuration. If they are not, an error message will appear in the instruction box stating: 'The scanned VIN does not belong to the selected mode (PRD)'.

 
                                                    
	You have selected EJO mode. Please ensure that the scanned or entered VIN and the selected active library (3W_Diagnostics, TPMS, or IVCU) are valid under EJO configuration. If they are not, an error message will appear in the instruction box stating: 'The scanned VIN does not belong to the selected mode (EJO)'.
 
   2.3.3 Test Completion:
	'All tests passed successfully!' will appear in the result box for U666/N603 when all test cases have been completed. In order to prepare the system for the subsequent VIN entry, this message is displayed for ten seconds before automatically resetting.
 

	'All tests passed successfully!' will appear in the result box for iQube ST cars once all test cases have been successfully completed. This notification will automatically disappear after ten seconds, enabling the operator to go on to the following validation cycle.
 

	If any of the test cases in the U666/N603 models fail, the relevant result box will show the error message related to that test. The test sequence stops instantly if it fails, and the program resets after 15 seconds to enable a new VIN scan and resume the validation procedure.
 
                                    
	If a test case fails in the iQube ST model, the result box will display the pertinent error message. After a 15-second pause, the program will reset itself and terminate the sequence execution, readying it for the subsequent VIN scan and test cycle.

 
2.3.4 Reset Process

	The application clears the VIN input, resets the progress bar, and resets for the next test cycle automatically with the given timeout and the message “Scan VIN to start next test cycle…” in the instruction box.
   
3. Track and Trace
	Within the MCU module configuration for the specified SKU number, the Vehicle ID parameter is defined in the Controller Configuration section of Track and Trace (T&T). This setup ensures that the Vehicle ID generated during the execution cycle is correctly associated with the corresponding work center and SKU, thereby enabling complete traceability across the process. Through this configuration, T&T automatically records and validates the Vehicle ID against the expected reference data, ensuring data integrity and consistency.
 
	The Phase Angle parameter in the MCU module is configured in the Controller Configuration section of T&T for the respective work center and SKU number. This configuration ensures that the phase offset angle retrieved from the ECU is captured, logged, and accurately linked to the vehicle record in T&T. By integrating this parameter, T&T establishes a reliable audit trail for phase angle data, supporting quality validation and process compliance.
 
4. Log Validation
4.1 File Location:
	Directory: “D:\Python\TVS NIRIX\test results”
	Filename Format: <VIN>_<YYYYMMDD_HHMMSS>.txt 
4.2 File Structure
4.2.1 IQube ST Logs:
VIN NUMBER      : MD626AM11S1G15083
TEST STATUS    : OK
DATE            	     : 2025-07-24 14:05:28
API Request: http://10.121.2.107:3000/vehicles/flashFile/prd/MD626AM11S1G15083
API Response:
 

Test_Sequence: API_CALL
Front_MAC_ID: C06380910000
Rear_MAC_ID: C0638091DDDD
Status: Passed
Cycle Time: 0.16 sec
……….
4.2.2 U666/N603 Logs:
VIN NUMBER      : MD6EVM1D8S4G00210
TEST STATUS    : OK
DATE            	     : 2025-07-03 15:10:56
API Request:http://10.121.2.107:3000/vehicles/flashFile/EJO/MD6EVM1D8S4G00210

API Response:
 
 
Test_Sequence: Battery SOC
Tx_Can_id: 0x775
Rx Hex_ID: 01 00 02 22 00 00 1A 00
Rx Dec_ID: 1 0 2 34 0 0 26 0
BMS SOC: 34 %
Status: Passed
Cycle Time: 0.47 sec
 
Test Sequence: Battery_Presence
Tx_Can_id: 0x22
Rx: 19 69 4E 0C 03 E8 05 97
Tx_Can_id: 0x2e
Rx: 83 65 89 64 00 00 00 00
Tx_Can_id: 0x23
Rx: 1E 0A 14 32 00 00 01 91
Tx_Can_id: 0x2d
Rx: 00 00 00 00 00 00 00 00
Tx_Can_id: 0x2f
Rx: 00 38 C5 00 37 60 00 00
Status: Passed
Cycle Time: 1.75 sec
 ………..


4.3	Overview of Logs:
4.3.1	Header Information
	VIN Number – Unique identifier for the vehicle (e.g., MD6EVM1D8S4G00210). It must be 17 characters long and start with “MD6.”

	Test Status – Indicates the overall test result (OK or NOK). NOK means at least one test failed.
	Date – Timestamp when the log was generated (e.g., 2025-07-03 15:10:56).
	API Request – The API endpoint used (e.g., http://10.121.2.107:3000/...). Verify that the selected mode (PRD or EJO) matches the VIN.
	API Response – JSON output containing:
•	Status Code (100 = success)
•	Error Message (if any)
•	data (module configurations such as VCU, MCU, etc.)
Check for missing modules (e.g., IPC in TPMS) that may trigger fallback processes.
4.3.2 Test Sequences
	Test Sequence Name – Name of the specific test.
	Tx CAN ID – CAN ID used for transmitting the request to the vehicle (e.g., 0x775).
	Rx Hex ID / Rx Hex – Received CAN message in hexadecimal format (e.g., 01 00 02 22 00 00 1A 00) showing the raw response.
	Rx Dec ID / Rx Dec – Decimal representation of the received bytes (e.g., 1 0 2 34 0 0 26 0) for easier interpretation of values such as SOC or version.
	Additional Data – Processed values derived from the raw data (e.g., BMS SOC: 34%, Version: 2.0.19, Vehicle Phase Offset Angle: -86.78). Compare against API txbytes for validation.
	Status – Displays Passed or Failed. Failures (e.g., VCU_Version: Not detected) may indicate communication issues or invalid data.
	Cycle Time – Execution time for the individual test (e.g., 0.47 sec). Useful for tracking performance and detecting delays.
4.3.3 Cycle Time Summary
	Start Cycle Time – Timestamp when testing began (e.g., 2025-07-03 15:10:21).
	Total Cycle Time – Timestamp when testing ended (e.g., 2025-07-03 15:10:56). The difference (e.g., 35 sec) reflects the overall test duration.
	Use this information to evaluate testing efficiency and pinpoint areas where delays may occur.

4.4     Auto Deletion of Logs:
	Execution: Runs at startup, scanning for .txt files, sorting by modification time, and deleting them as needed to manage storage with the separate sub program log_cleanup.py
	Log Visibility: Cleanup actions may appear in console output, not test logs. Check the log folder to confirm only recent files remain, and review log_cleanup.py for specific criteria like max_age_days or max_files.
5. SOFTWARE UPDATES
5.1 TVS NIRIX V1.1:
	Clean UI with a light theme background and a minimized window.
	Instruction Box with the proper mode API mode selection.
	Test Sequence failure with no attempts and a timeout.
	Test Sequence stoppage for the next cycle and not storing the log files.
	Cycle time of each subprogram is not added to logs after the test completion.
5.2 TVS NIRIX V1.2:
	Maximized Window with a better slider visibility and adjustable columns for the table.
	Test Sequence gets passed, if it is passed in the retry attempts or else it fails.
	Test Sequence will not stop in the next cycle; it will stop once we close the GUI.
	Added Start_Cycle_Time, Total_Cycle_Time and Cycle time completion for each subprogram
5.3 TVS NIRIX V1.4:
	Maximized Window with a better slider visibility and adjustable columns for the table.
	Added cycle time in the log for each sub program, when any of the sub program fails the cycle time also stops according to that and it won’t go to the next sub program.
	Added the TPMS active library that works when it is selected and also changed the table layout, log format, flag request for the status OK/NOK according to the active library when it is selected. 
