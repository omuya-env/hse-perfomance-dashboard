/*==================================================================*
 *  hse_charts.sas                                                  *
 *  HSE Performance Dashboard - optional SAS analysis module        *
 *                                                                  *
 *  Input : incident_log_clean_SYNTHETIC.csv (synthetic data)       *
 *  Output: monthly KPI table, study-period KPIs, TRIR/LTIF trend,  *
 *          near-miss bar chart, department Pareto, heatmap         *
 *                                                                  *
 *  HOW TO RUN (SAS OnDemand for Academics):                        *
 *    1. Upload incident_log_clean_SYNTHETIC.csv to your home       *
 *       folder (Files > Home in SAS Studio).                       *
 *    2. Put your own home path in the %LET below.                  *
 *    3. Run the whole file, or each section in order.              *
 *                                                                  *
 *  NOTE: exposure uses a fixed 21.7 average working days per       *
 *  month (500 employees x 8 h x 21.7 days = 86,800 man-hours).     *
 *  The Python pipeline derives exact working days per month;       *
 *  SAS keeps the exposure simple on purpose.                       *
 *==================================================================*/

/* EDIT THIS PATH to your SAS OnDemand home folder */
%LET inpath = /home/uXXXXXXX/incident_log_clean_SYNTHETIC.csv;

%LET EMP  = 500;
%LET HRS  = 8;
%LET DAYS = 21.7;
%LET MH_PER_MONTH = %SYSEVALF(&EMP * &HRS * &DAYS);   /* 86,800 */
%LET N_MONTHS = 18;

/*------------------------------------------------------------------*
 * 1. IMPORT                                                        *
 *------------------------------------------------------------------*/
PROC IMPORT DATAFILE="&inpath"
    OUT=WORK.incidents
    DBMS=CSV
    REPLACE;
    GETNAMES=YES;
    GUESSINGROWS=1000;
RUN;

/* Normalise the date column whether PROC IMPORT read it as
   character ($10, e.g. 2025-01-15) or as a SAS date. */
DATA WORK.incidents;
    SET WORK.incidents;
    IF VTYPE(date) = 'C' THEN date_num = INPUT(date, ANYDTDTE10.);
    ELSE date_num = date;
    DROP date;
    RENAME date_num = date;
    FORMAT date YYMMDD10.;
RUN;

/* Month key (first day of the incident's month) */
DATA WORK.incidents;
    SET WORK.incidents;
    month = INTNX('MONTH', date, 0, 'B');
    FORMAT month MONYY7.;
RUN;

PROC CONTENTS DATA=WORK.incidents SHORT; RUN;

/*------------------------------------------------------------------*
 * 2. MONTHLY KPI TABLE                                             *
 *------------------------------------------------------------------*/
PROC SQL;
    CREATE TABLE WORK.monthly_kpi AS
    SELECT month,
           COUNT(*)                                     AS total_events,
           SUM(event_type = 'Near Miss')                AS near_miss,
           SUM(event_type = 'First Aid')                AS first_aid,
           SUM(event_type = 'Medical Treatment')        AS medical_treatment,
           SUM(event_type = 'Lost Time Injury')         AS lti,
           SUM(days_lost)                               AS days_lost,
           CALCULATED lti * 1000000 / &MH_PER_MONTH     AS LTIF     FORMAT 8.2,
           (CALCULATED medical_treatment + CALCULATED lti)
                * 200000 / &MH_PER_MONTH                AS TRIR     FORMAT 8.2,
           CALCULATED days_lost * 1000000 / &MH_PER_MONTH AS Severity FORMAT 8.2
    FROM WORK.incidents
    GROUP BY month;
QUIT;

/* 18-month skeleton so quiet months still appear as zero rows */
DATA WORK.month_skeleton;
    DO d = '01JAN2025'D TO '01JUN2026'D BY 30;
        month = INTNX('MONTH', d, 0, 'B');
        OUTPUT;
    END;
    KEEP month;
    FORMAT month MONYY7.;
RUN;

PROC SORT DATA=WORK.month_skeleton NODUPKEY; BY month; RUN;

PROC SQL;
    CREATE TABLE WORK.kpi_final AS
    SELECT s.month,
           COALESCE(k.total_events, 0)      AS total_events,
           COALESCE(k.near_miss, 0)         AS near_miss,
           COALESCE(k.first_aid, 0)         AS first_aid,
           COALESCE(k.medical_treatment, 0) AS medical_treatment,
           COALESCE(k.lti, 0)               AS lti,
           COALESCE(k.days_lost, 0)         AS days_lost,
           COALESCE(k.LTIF, 0)              AS LTIF,
           COALESCE(k.TRIR, 0)              AS TRIR,
           COALESCE(k.Severity, 0)          AS Severity
    FROM WORK.month_skeleton s
    LEFT JOIN WORK.monthly_kpi k
      ON s.month = k.month
    ORDER BY s.month;
QUIT;

TITLE "Monthly HSE KPIs (SYNTHETIC data)";
PROC PRINT DATA=WORK.kpi_final NOOBS;
    VAR month total_events near_miss lti days_lost LTIF TRIR Severity;
RUN;

/*------------------------------------------------------------------*
 * 3. STUDY-PERIOD KPI SUMMARY                                      *
 *------------------------------------------------------------------*/
PROC MEANS DATA=WORK.incidents N SUM MEAN MIN MAX MAXDEC=1;
    VAR days_lost;
    CLASS event_type;
    TITLE "Days lost by event type (SYNTHETIC data)";
RUN;

PROC SQL;
    TITLE "Study-period KPIs, exposure &MH_PER_MONTH. man-hours/month (SYNTHETIC data)";
    SELECT SUM(event_type = 'Lost Time Injury')          AS total_lti,
           (SUM(event_type = 'Medical Treatment')
            + SUM(event_type = 'Lost Time Injury'))      AS total_recordables,
           SUM(days_lost)                                AS total_days_lost,
           &MH_PER_MONTH * &N_MONTHS                     AS total_man_hours FORMAT COMMA12.,
           CALCULATED total_lti * 1000000
               / CALCULATED total_man_hours              AS LTIF     FORMAT 8.2,
           CALCULATED total_recordables * 200000
               / CALCULATED total_man_hours              AS TRIR     FORMAT 8.2,
           CALCULATED total_days_lost * 1000000
               / CALCULATED total_man_hours              AS Severity FORMAT 8.2
    FROM WORK.incidents;
QUIT;

/*------------------------------------------------------------------*
 * 4. TREND CHARTS                                                  *
 *------------------------------------------------------------------*/
ODS GRAPHICS ON;
ODS HTML STYLE=HTMLBlue;

TITLE "Monthly TRIR and LTIF trend (SYNTHETIC data)";
PROC SGPLOT DATA=WORK.kpi_final;
    SERIES X=month Y=TRIR / MARKERS LINEATTRS=(THICKNESS=2);
    SERIES X=month Y=LTIF / MARKERS LINEATTRS=(THICKNESS=2 PATTERN=2);
    REFLINE 3.0 / AXIS=Y LABEL="Target 3.0" LINEATTRS=(PATTERN=20);
    XAXIS LABEL="Month";
    YAXIS LABEL="Rate";
RUN;

TITLE "Near-miss reporting by month, leading indicator (SYNTHETIC data)";
PROC SGPLOT DATA=WORK.kpi_final;
    VBAR month / RESPONSE=near_miss FILLATTRS=(COLOR=steelblue);
    XAXIS LABEL="Month" FITPOLICY=THIN;
    YAXIS LABEL="Near misses";
RUN;

/*------------------------------------------------------------------*
 * 5. PARETO OF INCIDENTS BY DEPARTMENT                             *
 *------------------------------------------------------------------*/
PROC SQL;
    CREATE TABLE WORK.dept_counts AS
    SELECT department,
           COUNT(*) AS incidents
    FROM WORK.incidents
    GROUP BY department
    ORDER BY incidents DESC, department;
QUIT;

/* Cumulative percentage in Pareto order (small table, subquery is fine) */
PROC SQL;
    CREATE TABLE WORK.dept_pareto AS
    SELECT d.department,
           d.incidents,
           (SELECT SUM(c.incidents)
            FROM WORK.dept_counts c
            WHERE (c.incidents > d.incidents)
               OR (c.incidents = d.incidents AND c.department <= d.department)
           ) * 100 / (SELECT SUM(incidents) FROM WORK.dept_counts) AS cum_pct
    FROM WORK.dept_counts d
    ORDER BY d.incidents DESC, d.department;
QUIT;

TITLE "Pareto of incidents by department (SYNTHETIC data)";
PROC SGPLOT DATA=WORK.dept_pareto;
    VBARPARM category=department RESPONSE=incidents / FILLATTRS=(COLOR=steelblue);
    SERIES X=department Y=cum_pct / Y2AXIS MARKERS
           LINEATTRS=(COLOR=red THICKNESS=2);
    Y2AXIS LABEL="Cumulative %" MIN=0 MAX=100;
    YAXIS LABEL="Incidents";
RUN;

/*------------------------------------------------------------------*
 * 6. HEATMAP: DEPARTMENT x EVENT TYPE                              *
 *------------------------------------------------------------------*/
TITLE "Incident heatmap: department x event type (SYNTHETIC data)";
PROC SGPLOT DATA=WORK.incidents;
    HEATMAP X=department Y=event_type / COLORMODEL=Blues;
    XAXIS LABEL="Department";
    YAXIS LABEL="Event type";
RUN;

ODS HTML CLOSE;
ODS GRAPHICS OFF;
TITLE;
