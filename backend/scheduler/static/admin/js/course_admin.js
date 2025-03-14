document.addEventListener('DOMContentLoaded', function() {
    // Initial setup when the page loads
    var requirementType = document.querySelector('select[name="student_count_requirement_type"]');
    if (requirementType) {
        toggleRequiredStudentCount(requirementType.value);
    }
});

function toggleRequiredStudentCount(value) {
    var requiredCountField = document.querySelector('.field-required_student_count');
    if (!requiredCountField) return;

    if (value === 'FULL_GRADE') {
        requiredCountField.style.display = 'none';
    } else {
        requiredCountField.style.display = 'block';
    }
} 