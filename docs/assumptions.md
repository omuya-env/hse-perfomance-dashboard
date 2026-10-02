# Synthetic HSE Data - Generation Assumptions

## Purpose

The dataset is synthetic because, usually, operating companies do not disclose their internal incident logs with enough detail for this portfolio project.

The dataset is generated for one industrial site within 18 months and intended to demonstrate the HSE analyst workflow to clean the incident records, calculate the monthly performance indicators, detect deterioration and make a management report.

## Site profile

* Employees: 500
* Period: 18 months
* Safe man-hours: derived, about 86,800 per month (500 employees x 8-hour shifts x average 21.7 working days)
* Departments and headcount:

  * Production: 220
  * Maintenance: 130
  * Logistics: 80
  * Warehouse: 70

The man-hours basis is deliberately realistic so that TRIR (recordables x 200,000 / hours) lands in the range real manufacturing sites report (roughly 1 to 6). The original build-plan figure of 25,000 man-hours per month was inconsistent with a 500-person site and would have produced implausible KPI values; the KPI calculations in this project therefore use the derived exposure above.

## Expected event distribution

The generator will aim to have approximately:

* 85% Near Miss
* 10% First Aid
* 4% Medical Treatment
* 1% Lost Time Injury

These percentages are targets rather than mandatory requirements. The generator is expected to have a variation in results from month to month.

## Performance pattern

The site will be modelled with three major periods:

### Period 1 - Improvement

The first few months will have gradual improvement in recordable incidents and other lagging indicators.

### Period 2 - Deterioration

The period with a bad quarter introduces the increase in incident activity and lost-time incidents.

The maintenance will be used as the department with deterioration during this period to give an opportunity to analyze some operational problem.

### Period 3 - Recovery

The last few months will see the recovery of the performance to the previous levels.

## Realism requirements

The generator should introduce the variation rather than create the identical monthly numbers.

The variation can be introduced in:

* the number of incidents
* department
* shift
* event type
* causes
* affected body part
* contractor
* days lost

The generator should not make all the fields independent from each other. Some causes should be typical for certain departments and some event types can lead to lost days more often.

## Bad-quarter design

The bad quarter should not simply increase the number of incidents in all categories.

The deterioration will be concentrated in certain areas like:

* maintenance
* equipment-related incidents
* unsafe condition
* manual handling
* selected shifts

This way, it will give an opportunity to find out the probable cause in the further analysis.

## Leading indicator: synthetic inspection programme

The incident log alone contains no leading indicator, so the project adds a synthetic monthly safety-inspection series in `src/config.py` (seeded, reproducible):

* about 54 inspections per month during improvement months
* a deliberate dip to about 38 during the bad quarter (inspection effort diverted to firefighting)
* about 50 during recovery

Poisson variation is applied on top of these means. The series exists to power the leading-vs-lagging comparison on the dashboard and should be read as a modelled programme, not as data from a real audit schedule.

## Synthetic data labeling

Each synthetic data file must have the `SYNTHETIC` word in the name.

The data and the project documentation must explicitly mention that the records are synthetic and are not the real company incident records.

## Limitations

Since the dataset is synthetic:

* the frequency of incidents is simulated
* the relations between causes are modelling assumptions
* the KPI trends are specifically designed for the analysis
* the findings cannot be represented as HSE statistics