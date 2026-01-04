-- Migration: Add recurring and scheduled task support
-- Date: 2026-01-04
--
-- This migration adds support for:
-- 1. Recurring tasks (e.g., "exercise every week")
-- 2. Scheduled tasks with due dates (e.g., "submit report by Jan 15")
--
-- Usage:
--   sqlite3 data/activities.db < migrations/add_recurring_scheduled.sql

-- Add new columns to activities table
ALTER TABLE activities ADD COLUMN recurrence_days INTEGER CHECK(recurrence_days IS NULL OR recurrence_days > 0);
ALTER TABLE activities ADD COLUMN last_completed_at TIMESTAMP;
ALTER TABLE activities ADD COLUMN due_date TIMESTAMP;
ALTER TABLE activities ADD COLUMN next_due_date TIMESTAMP;

-- Add indexes for performance
CREATE INDEX idx_activities_recurrence ON activities(recurrence_days);
CREATE INDEX idx_activities_due_date ON activities(due_date);
CREATE INDEX idx_activities_next_due_date ON activities(next_due_date);

-- Validation rules (enforced in application layer):
-- 1. recurrence_days requires completable = 1
-- 2. due_date requires completable = 1
-- 3. recurrence_days and due_date are mutually exclusive (can't be both)
-- 4. last_completed_at should only be set when recurrence_days IS NOT NULL
-- 5. next_due_date should only be set when recurrence_days IS NOT NULL
