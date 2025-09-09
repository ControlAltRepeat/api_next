// Copyright (c) 2025, API Next and contributors
// For license information, please see license.txt

frappe.pages['job-workflow-dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Job Order Workflow Dashboard',
		single_column: true
	});

	// Add custom buttons
	page.add_menu_item(__('Export Report'), function() {
		export_workflow_report();
	});

	page.add_menu_item(__('Refresh Data'), function() {
		load_dashboard_data();
	});

	// Initialize dashboard
	new JobWorkflowDashboard(page);
};

class JobWorkflowDashboard {
	constructor(page) {
		this.page = page;
		this.wrapper = page.body;
		this.init();
	}

	init() {
		this.setup_layout();
		this.load_data();
	}

	setup_layout() {
		// Create main dashboard layout
		this.wrapper.innerHTML = `
			<div class="workflow-dashboard">
				<div class="row">
					<div class="col-md-3">
						<div class="card summary-card">
							<div class="card-header">
								<h5>Workflow Summary</h5>
							</div>
							<div class="card-body" id="workflow-summary">
								<div class="text-center">
									<div class="spinner-border" role="status">
										<span class="sr-only">Loading...</span>
									</div>
								</div>
							</div>
						</div>
					</div>
					<div class="col-md-9">
						<div class="card">
							<div class="card-header">
								<h5>Phase Distribution</h5>
							</div>
							<div class="card-body">
								<canvas id="phase-chart" width="400" height="200"></canvas>
							</div>
						</div>
					</div>
				</div>
				
				<div class="row mt-4">
					<div class="col-md-6">
						<div class="card">
							<div class="card-header">
								<h5>Active Jobs by Phase</h5>
							</div>
							<div class="card-body" id="active-jobs-table">
								<div class="text-center">
									<div class="spinner-border" role="status">
										<span class="sr-only">Loading...</span>
									</div>
								</div>
							</div>
						</div>
					</div>
					<div class="col-md-6">
						<div class="card">
							<div class="card-header">
								<h5>Bottleneck Analysis</h5>
							</div>
							<div class="card-body" id="bottleneck-analysis">
								<div class="text-center">
									<div class="spinner-border" role="status">
										<span class="sr-only">Loading...</span>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
				
				<div class="row mt-4">
					<div class="col-md-12">
						<div class="card">
							<div class="card-header">
								<h5>Recent Workflow Transitions</h5>
							</div>
							<div class="card-body" id="recent-transitions">
								<div class="text-center">
									<div class="spinner-border" role="status">
										<span class="sr-only">Loading...</span>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<style>
				.workflow-dashboard {
					padding: 20px;
				}
				.summary-card .metric {
					text-align: center;
					margin: 10px 0;
				}
				.summary-card .metric .value {
					font-size: 2em;
					font-weight: bold;
					color: #007bff;
				}
				.summary-card .metric .label {
					font-size: 0.9em;
					color: #666;
				}
				.phase-badge {
					display: inline-block;
					padding: 4px 8px;
					border-radius: 4px;
					font-size: 0.8em;
					font-weight: 500;
					margin: 2px;
				}
				.phase-submission { background-color: #e3f2fd; color: #1976d2; }
				.phase-estimation { background-color: #f3e5f5; color: #7b1fa2; }
				.phase-client-approval { background-color: #fff3e0; color: #f57c00; }
				.phase-planning { background-color: #e8f5e8; color: #388e3c; }
				.phase-prework { background-color: #fff8e1; color: #f9a825; }
				.phase-execution { background-color: #ffebee; color: #d32f2f; }
				.phase-review { background-color: #e1f5fe; color: #0288d1; }
				.phase-invoicing { background-color: #f1f8e9; color: #689f38; }
				.phase-closeout { background-color: #fce4ec; color: #c2185b; }
				.phase-archived { background-color: #f5f5f5; color: #616161; }
				.phase-cancelled { background-color: #ffcdd2; color: #d32f2f; }
				
				.bottleneck-item {
					display: flex;
					justify-content: space-between;
					align-items: center;
					padding: 8px 0;
					border-bottom: 1px solid #eee;
				}
				.bottleneck-item:last-child {
					border-bottom: none;
				}
				.duration-bar {
					height: 20px;
					background-color: #007bff;
					border-radius: 10px;
					min-width: 20px;
				}
			</style>
		`;
	}

	load_data() {
		// Load workflow metrics
		this.load_workflow_metrics();
		
		// Load active jobs
		this.load_active_jobs();
		
		// Load recent transitions
		this.load_recent_transitions();
	}

	load_workflow_metrics() {
		frappe.call({
			method: 'api_next.job_management.doctype.job_order_workflow_history.job_order_workflow_history.get_workflow_metrics',
			callback: (r) => {
				if (r.message) {
					this.render_workflow_summary(r.message);
					this.render_bottleneck_analysis(r.message);
				}
			}
		});
	}

	load_active_jobs() {
		frappe.call({
			method: 'frappe.desk.query_report.run',
			args: {
				'report_name': 'Job Order Workflow Status',
				'filters': {}
			},
			callback: (r) => {
				if (r.message) {
					this.render_active_jobs_table(r.message.result);
					this.render_phase_chart(r.message.result);
				}
			}
		});
	}

	load_recent_transitions() {
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				'doctype': 'Job Order Workflow History',
				'fields': ['job_order', 'from_phase', 'to_phase', 'transition_date', 'user', 'user_role'],
				'order_by': 'transition_date desc',
				'limit': 20
			},
			callback: (r) => {
				if (r.message) {
					this.render_recent_transitions(r.message);
				}
			}
		});
	}

	render_workflow_summary(metrics) {
		const summaryHtml = `
			<div class="metric">
				<div class="value">${metrics.total_jobs_tracked || 0}</div>
				<div class="label">Total Jobs</div>
			</div>
			<div class="metric">
				<div class="value">${metrics.completed_jobs || 0}</div>
				<div class="label">Completed Jobs</div>
			</div>
			<div class="metric">
				<div class="value">${(metrics.completion_rate || 0).toFixed(1)}%</div>
				<div class="label">Completion Rate</div>
			</div>
			<div class="metric">
				<div class="value">${(metrics.average_completion_time_hours || 0).toFixed(1)}h</div>
				<div class="label">Avg Completion Time</div>
			</div>
		`;
		
		document.getElementById('workflow-summary').innerHTML = summaryHtml;
	}

	render_bottleneck_analysis(metrics) {
		if (!metrics.bottleneck_phases || metrics.bottleneck_phases.length === 0) {
			document.getElementById('bottleneck-analysis').innerHTML = '<p class="text-muted">No bottleneck data available</p>';
			return;
		}

		const maxDuration = Math.max(...metrics.bottleneck_phases.map(item => item[1]));
		
		const bottleneckHtml = metrics.bottleneck_phases.map(([phase, duration]) => {
			const percentage = (duration / maxDuration) * 100;
			return `
				<div class="bottleneck-item">
					<div>
						<strong>${phase}</strong><br>
						<small>${duration.toFixed(1)} hours avg</small>
					</div>
					<div style="width: 100px;">
						<div class="duration-bar" style="width: ${percentage}%;"></div>
					</div>
				</div>
			`;
		}).join('');

		document.getElementById('bottleneck-analysis').innerHTML = bottleneckHtml;
	}

	render_active_jobs_table(data) {
		if (!data || data.length === 0) {
			document.getElementById('active-jobs-table').innerHTML = '<p class="text-muted">No active jobs found</p>';
			return;
		}

		// Group jobs by phase
		const jobsByPhase = {};
		data.forEach(job => {
			const phase = job.workflow_state || 'Unknown';
			if (!jobsByPhase[phase]) {
				jobsByPhase[phase] = [];
			}
			jobsByPhase[phase].push(job);
		});

		let tableHtml = '<div class="table-responsive"><table class="table table-sm">';
		tableHtml += '<thead><tr><th>Phase</th><th>Job Count</th><th>Jobs</th></tr></thead><tbody>';

		Object.entries(jobsByPhase).forEach(([phase, jobs]) => {
			const phaseClass = this.getPhaseClass(phase);
			const jobLinks = jobs.slice(0, 3).map(job => 
				`<a href="/app/job-order/${job.name}" target="_blank">${job.name}</a>`
			).join(', ');
			const moreText = jobs.length > 3 ? ` and ${jobs.length - 3} more` : '';
			
			tableHtml += `
				<tr>
					<td><span class="phase-badge ${phaseClass}">${phase}</span></td>
					<td><strong>${jobs.length}</strong></td>
					<td>${jobLinks}${moreText}</td>
				</tr>
			`;
		});

		tableHtml += '</tbody></table></div>';
		document.getElementById('active-jobs-table').innerHTML = tableHtml;
	}

	render_phase_chart(data) {
		// Count jobs by phase
		const phaseCounts = {};
		data.forEach(job => {
			const phase = job.workflow_state || 'Unknown';
			phaseCounts[phase] = (phaseCounts[phase] || 0) + 1;
		});

		const ctx = document.getElementById('phase-chart').getContext('2d');
		
		// Create chart if Chart.js is available
		if (typeof Chart !== 'undefined') {
			new Chart(ctx, {
				type: 'doughnut',
				data: {
					labels: Object.keys(phaseCounts),
					datasets: [{
						data: Object.values(phaseCounts),
						backgroundColor: [
							'#e3f2fd', '#f3e5f5', '#fff3e0', '#e8f5e8',
							'#fff8e1', '#ffebee', '#e1f5fe', '#f1f8e9',
							'#fce4ec', '#f5f5f5', '#ffcdd2'
						],
						borderColor: [
							'#1976d2', '#7b1fa2', '#f57c00', '#388e3c',
							'#f9a825', '#d32f2f', '#0288d1', '#689f38',
							'#c2185b', '#616161', '#d32f2f'
						],
						borderWidth: 2
					}]
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: {
						legend: {
							position: 'right'
						}
					}
				}
			});
		} else {
			// Fallback if Chart.js is not available
			ctx.fillText('Chart.js not loaded', 10, 50);
		}
	}

	render_recent_transitions(transitions) {
		if (!transitions || transitions.length === 0) {
			document.getElementById('recent-transitions').innerHTML = '<p class="text-muted">No recent transitions found</p>';
			return;
		}

		let tableHtml = '<div class="table-responsive"><table class="table table-sm">';
		tableHtml += '<thead><tr><th>Job Order</th><th>Transition</th><th>User</th><th>Role</th><th>Date</th></tr></thead><tbody>';

		transitions.forEach(transition => {
			const fromClass = this.getPhaseClass(transition.from_phase);
			const toClass = this.getPhaseClass(transition.to_phase);
			const transitionDate = new Date(transition.transition_date).toLocaleString();
			
			tableHtml += `
				<tr>
					<td><a href="/app/job-order/${transition.job_order}" target="_blank">${transition.job_order}</a></td>
					<td>
						${transition.from_phase ? `<span class="phase-badge ${fromClass}">${transition.from_phase}</span>` : ''}
						${transition.from_phase ? ' → ' : ''}
						<span class="phase-badge ${toClass}">${transition.to_phase}</span>
					</td>
					<td>${transition.user}</td>
					<td>${transition.user_role || 'User'}</td>
					<td><small>${transitionDate}</small></td>
				</tr>
			`;
		});

		tableHtml += '</tbody></table></div>';
		document.getElementById('recent-transitions').innerHTML = tableHtml;
	}

	getPhaseClass(phase) {
		if (!phase) return '';
		return 'phase-' + phase.toLowerCase().replace(/\s+/g, '-');
	}
}

function export_workflow_report() {
	frappe.call({
		method: 'api_next.workflows.reports.export_workflow_report',
		callback: (r) => {
			if (r.message) {
				frappe.msgprint('Report exported successfully');
			}
		}
	});
}

function load_dashboard_data() {
	// Refresh the entire dashboard
	location.reload();
}