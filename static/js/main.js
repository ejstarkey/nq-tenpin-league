// NQ Tenpin League System - Main JavaScript

$(document).ready(function() {
    // Initialize DataTables on all tables with class 'datatable'
    if ($('.datatable').length) {
        $('.datatable').DataTable({
            "pageLength": 25,
            "responsive": true,
            "order": [[0, "asc"]],
            "language": {
                "search": "Search:",
                "lengthMenu": "Show _MENU_ entries",
                "info": "Showing _START_ to _END_ of _TOTAL_ entries",
                "paginate": {
                    "first": "First",
                    "last": "Last",
                    "next": "Next",
                    "previous": "Previous"
                }
            }
        });
    }

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // League creation wizard - toggle fine amount field
    $('#has_fines').change(function() {
        if ($(this).is(':checked')) {
            $('#fine_amount_group').slideDown();
            $('#fine_amount').prop('required', true);
        } else {
            $('#fine_amount_group').slideUp();
            $('#fine_amount').prop('required', false);
            $('#fine_amount').val('0');
        }
    });

    // League type selection - toggle team size field
    $('input[name="league_type"]').change(function() {
        if ($(this).val() === 'teams') {
            $('#team_size_group').slideDown();
            $('#players_per_team').prop('required', true);
        } else {
            $('#team_size_group').slideUp();
            $('#players_per_team').prop('required', false);
            $('#players_per_team').val('');
        }
    });

    // Attendance Grid Functionality
    if ($('.attendance-cell').length) {
        initializeAttendanceGrid();
    }

    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Form validation
    $('.needs-validation').on('submit', function(event) {
        if (!this.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
        }
        $(this).addClass('was-validated');
    });

    // CSV Import - show file name
    $('#csv_file').change(function() {
        var fileName = $(this).val().split('\\').pop();
        $(this).siblings('.form-file-label').html(fileName || 'Choose file...');
    });

    // Print functionality for reports
    $('#print-report').click(function() {
        window.print();
    });

    // Export to Excel functionality
    $('#export-excel').click(function() {
        var table = $('#report-table');
        var html = table.html();
        var url = 'data:application/vnd.ms-excel,' + encodeURIComponent(html);
        var downloadLink = document.createElement("a");
        document.body.appendChild(downloadLink);
        downloadLink.href = url;
        downloadLink.download = 'report_' + new Date().getTime() + '.xls';
        downloadLink.click();
        document.body.removeChild(downloadLink);
    });

    // Dashboard charts
    if ($('#attendance-chart').length) {
        initializeDashboardCharts();
    }

    // Live search for bowlers
    $('#bowler-search').on('keyup', function() {
        var value = $(this).val().toLowerCase();
        $('#bowlers-table tbody tr').filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });

    // Confirm delete actions
    $('.delete-confirm').click(function(e) {
        if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
            e.preventDefault();
        }
    });

    // TBA Verification Status Check
    $('#verify-tba-btn').click(function() {
        var btn = $(this);
        var originalText = btn.html();
        
        btn.prop('disabled', true);
        btn.html('<span class="spinner-border spinner-border-sm me-2"></span>Verifying...');
        
        $.post('/bowlers/verify-tba', function(response) {
            btn.prop('disabled', false);
            btn.html(originalText);
            location.reload();
        }).fail(function() {
            btn.prop('disabled', false);
            btn.html(originalText);
            alert('Verification failed. Please try again.');
        });
    });

    // Locker rental date validation
    $('#rental_start_date, #rental_end_date').change(function() {
        var startDate = new Date($('#rental_start_date').val());
        var endDate = new Date($('#rental_end_date').val());
        
        if (startDate && endDate && startDate >= endDate) {
            $('#rental_end_date').addClass('is-invalid');
            $('#date-error').show();
        } else {
            $('#rental_end_date').removeClass('is-invalid');
            $('#date-error').hide();
        }
    });
});

// Initialize Attendance Grid
function initializeAttendanceGrid() {
    // Handle cell clicks
    $('.attendance-cell').on('click', function(e) {
        e.preventDefault();
        var cell = $(this);
        var bowlerId = cell.data('bowler');
        var leagueId = cell.data('league');
        var weekNumber = cell.data('week');
        
        // Determine next status based on current
        var currentStatus = cell.data('status') || 'none';
        var newStatus = getNextStatus(currentStatus, e);
        
        // Update cell visually
        updateCellDisplay(cell, newStatus);
        
        // Send update to server
        updateAttendance(bowlerId, leagueId, weekNumber, newStatus);
    });

    // Right-click for missed status
    $('.attendance-cell').on('contextmenu', function(e) {
        e.preventDefault();
        var cell = $(this);
        var bowlerId = cell.data('bowler');
        var leagueId = cell.data('league');
        var weekNumber = cell.data('week');
        
        // Set to missed
        updateCellDisplay(cell, 'missed');
        updateAttendance(bowlerId, leagueId, weekNumber, 'missed');
        
        // Show fix button
        showFixButton(cell);
    });

    // Double-click for edit mode
    $('.attendance-cell').on('dblclick', function(e) {
        e.preventDefault();
        var cell = $(this);
        enterEditMode(cell);
    });
}

// Get next attendance status
function getNextStatus(current, event) {
    if (event.type === 'contextmenu') {
        return 'missed';
    }
    
    switch(current) {
        case 'none':
        case 'missed':
            return 'paid';
        case 'paid':
            return 'none';
        default:
            return 'paid';
    }
}

// Update cell display
function updateCellDisplay(cell, status) {
    cell.removeClass('paid missed fixed');
    cell.empty();
    
    switch(status) {
        case 'paid':
            cell.addClass('paid');
            cell.html('<i class="fas fa-check attendance-icon"></i>');
            break;
        case 'missed':
            cell.addClass('missed');
            cell.html('<i class="fas fa-times attendance-icon"></i>');
            break;
        case 'fixed':
            cell.addClass('fixed');
            cell.html('<i class="fas fa-wrench attendance-icon"></i>');
            break;
        default:
            cell.html('-');
    }
    
    cell.data('status', status);
}

// Show fix button for missed weeks
function showFixButton(cell) {
    if (!cell.find('.fix-btn').length) {
        var fixBtn = $('<button class="btn btn-sm btn-warning fix-btn mt-1">FIX</button>');
        cell.append(fixBtn);
        
        fixBtn.click(function(e) {
            e.stopPropagation();
            updateCellDisplay(cell, 'fixed');
            updateAttendance(
                cell.data('bowler'),
                cell.data('league'),
                cell.data('week'),
                'fixed'
            );
            $(this).remove();
        });
    }
}

// Enter edit mode for cell
function enterEditMode(cell) {
    var currentValue = cell.data('amount') || '0.00';
    var input = $('<input type="number" class="form-control form-control-sm" step="0.01">');
    input.val(currentValue);
    
    cell.empty().append(input);
    input.focus().select();
    
    input.on('blur', function() {
        var newAmount = parseFloat($(this).val()) || 0;
        exitEditMode(cell, newAmount);
    });
    
    input.on('keypress', function(e) {
        if (e.which === 13) { // Enter key
            $(this).blur();
        }
    });
}

// Exit edit mode
function exitEditMode(cell, amount) {
    var status = amount > 0 ? 'paid' : 'none';
    updateCellDisplay(cell, status);
    cell.data('amount', amount);
    
    // Update server with amount
    updateAttendanceWithAmount(
        cell.data('bowler'),
        cell.data('league'),
        cell.data('week'),
        status,
        amount
    );
}

// Update attendance on server
function updateAttendance(bowlerId, leagueId, weekNumber, status) {
    $.ajax({
        url: '/attendance/update',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            bowler_id: bowlerId,
            league_id: leagueId,
            week_number: weekNumber,
            status: status
        }),
        success: function(response) {
            // Update balance display
            if (response.balance !== undefined) {
                updateBalanceDisplay(bowlerId, response.balance);
            }
        },
        error: function() {
            alert('Failed to update attendance. Please try again.');
        }
    });
}

// Update attendance with amount
function updateAttendanceWithAmount(bowlerId, leagueId, weekNumber, status, amount) {
    $.ajax({
        url: '/attendance/update',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            bowler_id: bowlerId,
            league_id: leagueId,
            week_number: weekNumber,
            status: status,
            amount: amount
        }),
        success: function(response) {
            // Update balance display
            if (response.balance !== undefined) {
                updateBalanceDisplay(bowlerId, response.balance);
            }
        }
    });
}

// Update balance display
function updateBalanceDisplay(bowlerId, balance) {
    var balanceCell = $('#balance-' + bowlerId);
    if (balance > 0) {
        balanceCell.html('<span class="text-danger">$' + balance.toFixed(2) + '</span>');
    } else {
        balanceCell.html('<span class="text-success">$0.00</span>');
    }
}

// Initialize Dashboard Charts
function initializeDashboardCharts() {
    // Attendance Chart
    var ctx = document.getElementById('attendance-chart').getContext('2d');
    var attendanceChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Valid TBA', 'Invalid TBA', 'Pending'],
            datasets: [{
                data: [
                    parseInt($('#valid-tba').text()),
                    parseInt($('#invalid-tba').text()),
                    parseInt($('#pending-tba').text())
                ],
                backgroundColor: [
                    '#28a745',
                    '#dc3545',
                    '#ffc107'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#ffffff'
                    }
                }
            }
        }
    });

    // Revenue Chart
    if ($('#revenue-chart').length) {
        var ctx2 = document.getElementById('revenue-chart').getContext('2d');
        var revenueChart = new Chart(ctx2, {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6'],
                datasets: [{
                    label: 'Revenue',
                    data: [1200, 1900, 3000, 2500, 2700, 3200],
                    borderColor: '#e91e8c',
                    backgroundColor: 'rgba(233, 30, 140, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#ffffff',
                            callback: function(value) {
                                return '$' + value;
                            }
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#ffffff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#ffffff'
                        }
                    }
                }
            }
        });
    }
}

// Export functions for use in other scripts
window.NQTenpin = {
    updateAttendance: updateAttendance,
    updateBalanceDisplay: updateBalanceDisplay,
    initializeAttendanceGrid: initializeAttendanceGrid
};
