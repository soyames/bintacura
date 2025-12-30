
======================================================================
BINTACURA ENVIRONMENT CONFIGURATION
======================================================================
Environment:     PRODUCTION
Location:        LOCAL MACHINE
Region:          EU-NORTH-1
Debug Mode:      True
Database:        bintacura-db-gb.c9uwsww6o8ky.eu-north-1.rds.amazonaws.com
Email Backend:   SMTP
Security:        moderate
Local Port:      8080
======================================================================

BEGIN;
--
-- Create model Bed
--
CREATE TABLE "hospital_beds" ("id" uuid NOT NULL PRIMARY KEY, "bed_number" varchar(20) NOT NULL, "room_number" varchar(20) NOT NULL, "floor_number" varchar(10) NOT NULL, "bed_type" varchar(20) NOT NULL, "status" varchar(20) NOT NULL, "has_oxygen" boolean NOT NULL, "has_monitor" boolean NOT NULL, "is_iBINTAtion" boolean NOT NULL, "last_cleaned" timestamp with time zone NULL, "notes" text NOT NULL, "created_at" timestamp with time zone NOT NULL, "updated_at" timestamp with time zone NOT NULL, "department_id" uuid NOT NULL, "hospital_id" uuid NOT NULL);
--
-- Create model Admission
--
CREATE TABLE "hospital_admissions" ("id" uuid NOT NULL PRIMARY KEY, "admission_number" varchar(50) NOT NULL UNIQUE, "admission_type" varchar(20) NOT NULL, "status" varchar(20) NOT NULL, "chief_complaint" text NOT NULL, "diagnosis" text NOT NULL, "treatment_plan" text NOT NULL, "admission_date" timestamp with time zone NOT NULL, "expected_discharge_date" date NULL, "actual_discharge_date" timestamp with time zone NULL, "discharge_summary" text NOT NULL, "discharge_instructions" text NOT NULL, "follow_up_required" boolean NOT NULL, "follow_up_date" date NULL, "total_cost" integer NOT NULL, "insurance_coverage" integer NOT NULL, "patient_responsibility" integer NOT NULL, "notes" text NOT NULL, "created_at" timestamp with time zone NOT NULL, "updated_at" timestamp with time zone NOT NULL, "department_id" uuid NULL, "hospital_id" uuid NOT NULL, "patient_id" uuid NOT NULL, "bed_id" uuid NULL);
--
-- Create model HospitalBill
--
CREATE TABLE "hospital_bills" ("id" uuid NOT NULL PRIMARY KEY, "bill_number" varchar(50) NOT NULL UNIQUE, "status" varchar(20) NOT NULL, "total_amount" integer NOT NULL, "discount_amount" integer NOT NULL, "tax_amount" integer NOT NULL, "insurance_coverage" integer NOT NULL, "amount_paid" integer NOT NULL, "balance_due" integer NOT NULL, "due_date" date NULL, "billing_date" date NOT NULL, "notes" text NOT NULL, "created_at" timestamp with time zone NOT NULL, "updated_at" timestamp with time zone NOT NULL, "admission_id" uuid NULL, "hospital_id" uuid NOT NULL, "patient_id" uuid NOT NULL);
--
-- Create model BillItem
--
CREATE TABLE "hospital_bill_items" ("id" uuid NOT NULL PRIMARY KEY, "item_type" varchar(20) NOT NULL, "description" varchar(255) NOT NULL, "quantity" integer NOT NULL, "unit_price" integer NOT NULL, "total_price" integer NOT NULL, "date_of_service" date NOT NULL, "bill_id" uuid NOT NULL);
--
-- Create model HospitalStaff
--
CREATE TABLE "hospital_staff" ("id" uuid NOT NULL PRIMARY KEY, "full_name" varchar(255) NOT NULL, "email" varchar(254) NOT NULL, "phone_number" varchar(20) NOT NULL, "role" varchar(30) NOT NULL, "employment_type" varchar(20) NOT NULL, "license_number" varchar(100) NOT NULL, "specialization" varchar(255) NOT NULL, "hire_date" date NOT NULL, "end_date" date NULL, "is_active" boolean NOT NULL, "can_admit_patients" boolean NOT NULL, "can_discharge_patients" boolean NOT NULL, "can_prescribe" boolean NOT NULL, "can_perform_surgery" boolean NOT NULL, "can_manage_equipment" boolean NOT NULL, "can_manage_staff" boolean NOT NULL, "can_view_all_records" boolean NOT NULL, "shift_schedule" varchar(50) NOT NULL, "created_at" timestamp with time zone NOT NULL, "updated_at" timestamp with time zone NOT NULL, "department_id" uuid NULL, "hospital_id" uuid NOT NULL, "staff_member_id" uuid NULL);
--
-- Create model DepartmentTask
--
CREATE TABLE "department_tasks" ("id" uuid NOT NULL PRIMARY KEY, "title" varchar(255) NOT NULL, "description" text NOT NULL, "priority" varchar(10) NOT NULL, "status" varchar(20) NOT NULL, "due_date" timestamp with time zone NULL, "completed_at" timestamp with time zone NULL, "notes" text NOT NULL, "created_at" timestamp with time zone NOT NULL, "updated_at" timestamp with time zone NOT NULL, "department_id" uuid NOT NULL, "assigned_to_id" uuid NULL, "created_by_id" uuid NULL);
--
-- Add field admitting_doctor to admission
--
ALTER TABLE "hospital_admissions" ADD COLUMN "admitting_doctor_id" uuid NULL CONSTRAINT "hospital_admissions_admitting_doctor_id_2f7a1e94_fk_hospital_" REFERENCES "hospital_staff"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "hospital_admissions_admitting_doctor_id_2f7a1e94_fk_hospital_" IMMEDIATE;
--
-- Create model Payment
--
CREATE TABLE "hospital_payments" ("id" uuid NOT NULL PRIMARY KEY, "payment_number" varchar(50) NOT NULL UNIQUE, "amount" integer NOT NULL, "payment_method" varchar(20) NOT NULL, "transaction_ref" varchar(100) NOT NULL, "payment_date" timestamp with time zone NOT NULL, "notes" text NOT NULL, "created_at" timestamp with time zone NOT NULL, "bill_id" uuid NOT NULL, "hospital_id" uuid NOT NULL, "received_by_id" uuid NULL);
--
-- Create index hospital_be_hospita_b6bd2a_idx on field(s) hospital, status of model bed
--
CREATE INDEX "hospital_be_hospita_b6bd2a_idx" ON "hospital_beds" ("hospital_id", "status");
--
-- Create index hospital_be_departm_3d0974_idx on field(s) department, status of model bed
--
CREATE INDEX "hospital_be_departm_3d0974_idx" ON "hospital_beds" ("department_id", "status");
--
-- Alter unique_together for bed (1 constraint(s))
--
ALTER TABLE "hospital_beds" ADD CONSTRAINT "hospital_beds_hospital_id_bed_number_51df0a30_uniq" UNIQUE ("hospital_id", "bed_number");
--
-- Create index hospital_bi_hospita_6ddc23_idx on field(s) hospital, status of model hospitalbill
--
CREATE INDEX "hospital_bi_hospita_6ddc23_idx" ON "hospital_bills" ("hospital_id", "status");
--
-- Create index hospital_bi_patient_07fcd3_idx on field(s) patient of model hospitalbill
--
CREATE INDEX "hospital_bi_patient_07fcd3_idx" ON "hospital_bills" ("patient_id");
--
-- Create index hospital_bi_bill_nu_6e413c_idx on field(s) bill_number of model hospitalbill
--
CREATE INDEX "hospital_bi_bill_nu_6e413c_idx" ON "hospital_bills" ("bill_number");
--
-- Create index hospital_st_hospita_27cc4b_idx on field(s) hospital, is_active of model hospitalstaff
--
CREATE INDEX "hospital_st_hospita_27cc4b_idx" ON "hospital_staff" ("hospital_id", "is_active");
--
-- Create index hospital_st_departm_66bfbd_idx on field(s) department of model hospitalstaff
--
CREATE INDEX "hospital_st_departm_66bfbd_idx" ON "hospital_staff" ("department_id");
--
-- Create index hospital_st_role_224bb8_idx on field(s) role of model hospitalstaff
--
CREATE INDEX "hospital_st_role_224bb8_idx" ON "hospital_staff" ("role");
--
-- Create index department__departm_f0cbae_idx on field(s) department, status of model departmenttask
--
CREATE INDEX "department__departm_f0cbae_idx" ON "department_tasks" ("department_id", "status");
--
-- Create index department__assigne_41ab44_idx on field(s) assigned_to, status of model departmenttask
--
CREATE INDEX "department__assigne_41ab44_idx" ON "department_tasks" ("assigned_to_id", "status");
--
-- Create index department__priorit_3e7e2e_idx on field(s) priority of model departmenttask
--
CREATE INDEX "department__priorit_3e7e2e_idx" ON "department_tasks" ("priority");
--
-- Create index hospital_ad_hospita_5e824e_idx on field(s) hospital, status of model admission
--
CREATE INDEX "hospital_ad_hospita_5e824e_idx" ON "hospital_admissions" ("hospital_id", "status");
--
-- Create index hospital_ad_patient_69789d_idx on field(s) patient of model admission
--
CREATE INDEX "hospital_ad_patient_69789d_idx" ON "hospital_admissions" ("patient_id");
--
-- Create index hospital_ad_admissi_09eb07_idx on field(s) admission_number of model admission
--
CREATE INDEX "hospital_ad_admissi_09eb07_idx" ON "hospital_admissions" ("admission_number");
--
-- Create index hospital_ad_admissi_fcd20d_idx on field(s) admission_date of model admission
--
CREATE INDEX "hospital_ad_admissi_fcd20d_idx" ON "hospital_admissions" ("admission_date");
--
-- Create index hospital_pa_hospita_e6e3e2_idx on field(s) hospital, payment_date of model payment
--
CREATE INDEX "hospital_pa_hospita_e6e3e2_idx" ON "hospital_payments" ("hospital_id", "payment_date");
--
-- Create index hospital_pa_bill_id_7289e2_idx on field(s) bill of model payment
--
CREATE INDEX "hospital_pa_bill_id_7289e2_idx" ON "hospital_payments" ("bill_id");
--
-- Create index hospital_pa_payment_84aff7_idx on field(s) payment_number of model payment
--
CREATE INDEX "hospital_pa_payment_84aff7_idx" ON "hospital_payments" ("payment_number");
ALTER TABLE "hospital_beds" ADD CONSTRAINT "hospital_beds_department_id_0b7361a6_fk_departments_id" FOREIGN KEY ("department_id") REFERENCES "departments" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "hospital_beds" ADD CONSTRAINT "hospital_beds_hospital_id_3f50b7d1_fk_participants_uid" FOREIGN KEY ("hospital_id") REFERENCES "participants" ("uid") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "hospital_beds_department_id_0b7361a6" ON "hospital_beds" ("department_id");
CREATE INDEX "hospital_beds_hospital_id_3f50b7d1" ON "hospital_beds" ("hospital_id");
ALTER TABLE "hospital_admissions" ADD CONSTRAINT "hospital_admissions_department_id_e128ddc5_fk_departments_id" FOREIGN KEY ("department_id") REFERENCES "departments" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "hospital_admissions" ADD CONSTRAINT "hospital_admissions_hospital_id_eb9a2926_fk_participants_uid" FOREIGN KEY ("hospital_id") REFERENCES "participants" ("uid") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "hospital_admissions" ADD CONSTRAINT "hospital_admissions_patient_id_39bc485e_fk_participants_uid" FOREIGN KEY ("patient_id") REFERENCES "participants" ("uid") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "hospital_admissions" ADD CONSTRAINT "hospital_admissions_bed_id_5adbf7ff_fk_hospital_beds_id" FOREIGN KEY ("bed_id") REFERENCES "hospital_beds" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "hospital_admissions_admission_number_0764f98f_like" ON "hospital_admissions" ("admission_number" varchar_pattern_ops);
CREATE INDEX "hospital_admissions_department_id_e128ddc5" ON "hospital_admissions" ("department_id");
CREATE INDEX "hospital_admissions_hospital_id_eb9a2926" ON "hospital_admissions" ("hospital_id");
CREATE INDEX "hospital_admissions_patient_id_39bc485e" ON "hospital_admissions" ("patient_id");
CREATE INDEX "hospital_admissions_bed_id_5adbf7ff" ON "hospital_admissions" ("bed_id");
ALTER TABLE "hospital_bills" ADD CONSTRAINT "hospital_bills_admission_id_92c7c7af_fk_hospital_admissions_id" FOREIGN KEY ("admission_id") REFERENCES "hospital_admissions" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "hospital_bills" ADD CONSTRAINT "hospital_bills_hospital_id_16090615_fk_participants_uid" FOREIGN KEY ("hospital_id") REFERENCES "participants" ("uid") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "hospital_bills" ADD CONSTRAINT "hospital_bills_patient_id_35847e3a_fk_participants_uid" FOREIGN KEY ("patient_id") REFERENCES "participants" ("uid") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "hospital_bills_bill_number_debbfb42_like" ON "hospital_bills" ("bill_number" varchar_pattern_ops);
CREATE INDEX "hospital_bills_admission_id_92c7c7af" ON "hospital_bills" ("admission_id");
CREATE INDEX "hospital_bills_hospital_id_16090615" ON "hospital_bills" ("hospital_id");
CREATE INDEX "hospital_bills_patient_id_35847e3a" ON "hospital_bills" ("patient_id");
ALTER TABLE "hospital_bill_items" ADD CONSTRAINT "hospital_bill_items_bill_id_96474b16_fk_hospital_bills_id" FOREIGN KEY ("bill_id") REFERENCES "hospital_bills" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "hospital_bill_items_bill_id_96474b16" ON "hospital_bill_items" ("bill_id");
ALTER TABLE "hospital_staff" ADD CONSTRAINT "hospital_staff_department_id_6d81976f_fk_departments_id" FOREIGN KEY ("department_id") REFERENCES "departments" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "hospital_staff" ADD CONSTRAINT "hospital_staff_hospital_id_3284669a_fk_participants_uid" FOREIGN KEY ("hospital_id") REFERENCES "participants" ("uid") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "hospital_staff" ADD CONSTRAINT "hospital_staff_staff_member_id_971230de_fk_participants_uid" FOREIGN KEY ("staff_member_id") REFERENCES "participants" ("uid") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "hospital_staff_department_id_6d81976f" ON "hospital_staff" ("department_id");
CREATE INDEX "hospital_staff_hospital_id_3284669a" ON "hospital_staff" ("hospital_id");
CREATE INDEX "hospital_staff_staff_member_id_971230de" ON "hospital_staff" ("staff_member_id");
ALTER TABLE "department_tasks" ADD CONSTRAINT "department_tasks_department_id_7a9a4b9d_fk_departments_id" FOREIGN KEY ("department_id") REFERENCES "departments" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "department_tasks" ADD CONSTRAINT "department_tasks_assigned_to_id_5cc4e68a_fk_hospital_staff_id" FOREIGN KEY ("assigned_to_id") REFERENCES "hospital_staff" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "department_tasks" ADD CONSTRAINT "department_tasks_created_by_id_a5835d89_fk_hospital_staff_id" FOREIGN KEY ("created_by_id") REFERENCES "hospital_staff" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "department_tasks_department_id_7a9a4b9d" ON "department_tasks" ("department_id");
CREATE INDEX "department_tasks_assigned_to_id_5cc4e68a" ON "department_tasks" ("assigned_to_id");
CREATE INDEX "department_tasks_created_by_id_a5835d89" ON "department_tasks" ("created_by_id");
CREATE INDEX "hospital_admissions_admitting_doctor_id_2f7a1e94" ON "hospital_admissions" ("admitting_doctor_id");
ALTER TABLE "hospital_payments" ADD CONSTRAINT "hospital_payments_bill_id_07ce44c2_fk_hospital_bills_id" FOREIGN KEY ("bill_id") REFERENCES "hospital_bills" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "hospital_payments" ADD CONSTRAINT "hospital_payments_hospital_id_d06d249e_fk_participants_uid" FOREIGN KEY ("hospital_id") REFERENCES "participants" ("uid") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "hospital_payments" ADD CONSTRAINT "hospital_payments_received_by_id_e16d0e4e_fk_hospital_staff_id" FOREIGN KEY ("received_by_id") REFERENCES "hospital_staff" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "hospital_payments_payment_number_3166b3b3_like" ON "hospital_payments" ("payment_number" varchar_pattern_ops);
CREATE INDEX "hospital_payments_bill_id_07ce44c2" ON "hospital_payments" ("bill_id");
CREATE INDEX "hospital_payments_hospital_id_d06d249e" ON "hospital_payments" ("hospital_id");
CREATE INDEX "hospital_payments_received_by_id_e16d0e4e" ON "hospital_payments" ("received_by_id");
COMMIT;
