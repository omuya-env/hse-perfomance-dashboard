# HSE Incident Log - Data Dictionary

## Purpose of dataset

The given dataset represents a 18-months artificial incident log for one industrial operation site.

The dataset is created for HSE performance reporting, KPI calculation, trend analysis, department comparison and management reporting.

This is artificial data and does not refer to any company’s incident reports.

---

## Incident level fields

| Field           | Type     | Description                                                       |
| --------------- | -------- | -----------------------------------------------------------------|
| `incident_id`   | String   | Unique ID of incident/event                                        |
| `date`          | Date     | Date of incident                                                  |
| `shift`         | Category | Work shift in which the incident occurred                          |
| `department`    | Category | Department in which the incident happened                           |
| `event_type`    | Category | HSE event classification                                          |
| `body_part`     | Category | Affected body part, where necessary                                |
| `immediate_cause`| Category | Immediate unsafe act or unsafe condition causing the event        |
| `root_cause`    | Category | Root cause from 5-whys analysis                                    |
| `days_lost`     | Integer  | Number of days lost because of the incident                        |
| `contractor_flag`| Boolean  | Whether the incident was related to a contractor or not            |

---

## Allowed values

### Shift

* Day
* Evening
* Night

### Department

* Production
* Maintenance
* Logistics
* Warehouse

### Event type

* Near Miss
* First Aid
* Medical Treatment
* Lost Time Injury

### Body part

* None
* Head
* Eye
* Hand
* Arm
* Back
* Leg
* Foot
* Multiple

`None` is used for incidents when there was no injury.

### Immediate cause

* Unsafe Act
* Unsafe Condition
* Equipment Failure
* Inadequate PPE
* Poor Housekeeping
* Manual Handling
* Slips/Trips
* Vehicle/Traffic
* Chemical Exposure
* Electrical
* Other

### Root cause

* Inadequate Procedure
* Inadequate Training
* Poor Supervision
* Equipment Maintenance
* Risk Assessment Gap
* Housekeeping Management
* PPE Management
* Workload/Staffing
* Communication
* Environmental Conditions
* Other

### Contractor flag

* `TRUE`
* `FALSE`

---

## Data rules

1. Each `incident_id` is unique.
2. Each record must have a valid date in 18-months period of the study.
3. Each record belongs to exactly one department.
4. Each record belongs to exactly one event type.
5. `days_lost` must be equal to zero for Near Miss and First Aid events.
6. Medical Treatment events have zero days lost normally unless the assumptions of the project explicitly stated something else.
7. Lost Time Injury events must have at least one day lost.
8. `body_part` could be `None` for Near Miss events.
9. `contractor_flag` must contain either TRUE or FALSE value.
10. There should be no duplicate incident records in the cleaned dataset.

---

## Derived fields

The following fields will not be manually created in the incident log. They will be calculated during the analysis:

* `month`
* `year`
* `recordable_flag`
* `lti_flag`
* `near_miss_flag`
* `days_lost_flag`

These will be used to calculate monthly HSE KPIs.

---

## Dataset scope

Main dataset includes:

* One operation site
* 18 months period
* ~400-600 employees
* ~25,000 safe man-hours/month
* Monthly granularity for KPI analysis

Incident level data stays at individual-event level in order to conduct analysis of departments, causes, event types and severity.