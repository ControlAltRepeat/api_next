# Copyright (c) 2025, API Next and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime, time_diff_in_seconds

class JobOrderWorkflowHistory(Document):
    def autoname(self):
        # Generate name in format: JOB-YY-XXXXX-WF-###
        job_order_number = self.job_order
        if job_order_number:
            # Count existing workflow history records for this job order
            count = frappe.db.count(
                "Job Order Workflow History",
                filters={"job_order": job_order_number}
            )
            self.name = f"{job_order_number}-WF-{count + 1:03d}"
        else:
            self.name = make_autoname("WF-.YY.-.#####")
    
    def before_insert(self):
        # Set additional audit information
        self.ip_address = frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else None
        self.user_agent = frappe.get_request_header("User-Agent")
        
        # Set user role at time of transition
        user_roles = frappe.get_roles(self.user)
        # Get the primary role for this transition
        workflow_roles = [
            "Job Coordinator", "Estimator", "Client", "Sales Manager",
            "Project Manager", "Resource Coordinator", "Site Supervisor",
            "Technician", "Quality Inspector", "Billing Clerk",
            "Accountant", "Document Controller", "Material Coordinator",
            "Operations Manager"
        ]
        
        primary_role = "User"
        for role in workflow_roles:
            if role in user_roles:
                primary_role = role
                break
        
        self.user_role = primary_role
        
        # Calculate duration in previous phase
        if self.from_phase and self.job_order:
            self.calculate_phase_duration()
    
    def calculate_phase_duration(self):
        """Calculate how long the job order spent in the previous phase."""
        try:
            # Get the previous transition record for this job order
            previous_transition = frappe.get_all(
                "Job Order Workflow History",
                filters={
                    "job_order": self.job_order,
                    "to_phase": self.from_phase
                },
                fields=["transition_date"],
                order_by="transition_date desc",
                limit=1
            )
            
            if previous_transition:
                previous_date = previous_transition[0].transition_date
                current_date = self.transition_date
                
                # Calculate duration in seconds
                duration_seconds = time_diff_in_seconds(current_date, previous_date)
                
                # Convert to duration format (HH:MM:SS)
                hours = duration_seconds // 3600
                minutes = (duration_seconds % 3600) // 60
                seconds = duration_seconds % 60
                
                self.duration_in_previous_phase = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
        except Exception as e:
            frappe.log_error(f"Error calculating phase duration: {str(e)}")
    
    def validate(self):
        # Ensure transition_date is set
        if not self.transition_date:
            self.transition_date = now_datetime()
    
    @frappe.whitelist()
    def get_transition_analytics(self):
        """Get analytics for this transition."""
        return {
            "transition_type": self._get_transition_type(),
            "is_forward_transition": self._is_forward_transition(),
            "phase_duration": self.duration_in_previous_phase,
            "user_role": self.user_role,
            "transition_date": self.transition_date
        }
    
    def _get_transition_type(self):
        """Determine the type of transition."""
        if not self.from_phase:
            return "Initial"
        elif self.to_phase == "Cancelled":
            return "Cancellation"
        elif self.from_phase == "Cancelled":
            return "Reactivation"
        elif self._is_forward_transition():
            return "Forward"
        else:
            return "Backward"
    
    def _is_forward_transition(self):
        """Check if this is a forward transition in the workflow."""
        if not self.from_phase or not self.to_phase:
            return True
        
        # Define phase order
        phase_order = {
            "Submission": 1,
            "Estimation": 2,
            "Client Approval": 3,
            "Planning": 4,
            "Prework": 5,
            "Execution": 6,
            "Review": 7,
            "Invoicing": 8,
            "Closeout": 9,
            "Archived": 10,
            "Cancelled": 0
        }
        
        from_order = phase_order.get(self.from_phase, 0)
        to_order = phase_order.get(self.to_phase, 0)
        
        return to_order > from_order
    
    @staticmethod
    def get_job_workflow_summary(job_order):
        """Get workflow summary for a job order."""
        history = frappe.get_all(
            "Job Order Workflow History",
            filters={"job_order": job_order},
            fields=[
                "from_phase", "to_phase", "transition_date", "user",
                "user_role", "duration_in_previous_phase", "comment"
            ],
            order_by="transition_date asc"
        )
        
        if not history:
            return {
                "total_transitions": 0,
                "current_phase": "Submission",
                "total_duration": 0,
                "average_phase_duration": 0,
                "transitions": []
            }
        
        # Calculate metrics
        total_transitions = len(history)
        current_phase = history[-1].to_phase if history else "Submission"
        
        # Calculate total duration
        first_transition = history[0].transition_date
        last_transition = history[-1].transition_date
        total_duration_seconds = time_diff_in_seconds(last_transition, first_transition)
        
        # Calculate average phase duration
        phase_durations = []
        for record in history:
            if record.duration_in_previous_phase:
                # Parse duration string (HH:MM:SS)
                try:
                    time_parts = record.duration_in_previous_phase.split(":")
                    duration_seconds = (
                        int(time_parts[0]) * 3600 +
                        int(time_parts[1]) * 60 +
                        int(time_parts[2])
                    )
                    phase_durations.append(duration_seconds)
                except:
                    pass
        
        average_phase_duration = sum(phase_durations) / len(phase_durations) if phase_durations else 0
        
        return {
            "total_transitions": total_transitions,
            "current_phase": current_phase,
            "total_duration_hours": total_duration_seconds / 3600,
            "average_phase_duration_hours": average_phase_duration / 3600,
            "transitions": history,
            "phase_count": {
                "forward": len([h for h in history if h.to_phase not in ["Cancelled"]]),
                "backward": len([h for h in history if h.from_phase and h.to_phase in ["Submission", "Estimation", "Client Approval", "Planning", "Prework", "Execution", "Review"]]),
                "cancellations": len([h for h in history if h.to_phase == "Cancelled"])
            }
        }
    
    @staticmethod
    def get_workflow_metrics():
        """Get overall workflow metrics across all job orders."""
        # Get all workflow history
        all_history = frappe.get_all(
            "Job Order Workflow History",
            fields=[
                "job_order", "from_phase", "to_phase", "transition_date",
                "duration_in_previous_phase"
            ],
            order_by="transition_date desc",
            limit=1000  # Limit for performance
        )
        
        if not all_history:
            return {}
        
        # Group by job order
        job_metrics = {}
        for record in all_history:
            job_order = record.job_order
            if job_order not in job_metrics:
                job_metrics[job_order] = []
            job_metrics[job_order].append(record)
        
        # Calculate metrics
        completed_jobs = 0
        average_completion_time = 0
        phase_completion_rates = {}
        bottleneck_phases = {}
        
        for job_order, transitions in job_metrics.items():
            # Sort by transition date
            transitions.sort(key=lambda x: x.transition_date)
            
            # Check if job is completed
            last_phase = transitions[-1].to_phase if transitions else "Submission"
            if last_phase in ["Archived", "Completed"]:
                completed_jobs += 1
                
                # Calculate completion time
                first_transition = transitions[0].transition_date
                last_transition = transitions[-1].transition_date
                completion_time = time_diff_in_seconds(last_transition, first_transition)
                average_completion_time += completion_time
            
            # Track phase durations for bottleneck analysis
            for transition in transitions:
                if transition.duration_in_previous_phase and transition.from_phase:
                    phase = transition.from_phase
                    if phase not in bottleneck_phases:
                        bottleneck_phases[phase] = []
                    
                    try:
                        time_parts = transition.duration_in_previous_phase.split(":")
                        duration_seconds = (
                            int(time_parts[0]) * 3600 +
                            int(time_parts[1]) * 60 +
                            int(time_parts[2])
                        )
                        bottleneck_phases[phase].append(duration_seconds)
                    except:
                        pass
        
        # Calculate averages
        if completed_jobs > 0:
            average_completion_time = average_completion_time / completed_jobs / 3600  # Convert to hours
        
        # Calculate average duration for each phase
        phase_averages = {}
        for phase, durations in bottleneck_phases.items():
            if durations:
                phase_averages[phase] = sum(durations) / len(durations) / 3600  # Convert to hours
        
        return {
            "total_jobs_tracked": len(job_metrics),
            "completed_jobs": completed_jobs,
            "completion_rate": (completed_jobs / len(job_metrics)) * 100 if job_metrics else 0,
            "average_completion_time_hours": average_completion_time,
            "phase_average_durations": phase_averages,
            "bottleneck_phases": sorted(
                phase_averages.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]  # Top 5 longest phases
        }