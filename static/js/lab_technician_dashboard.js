function startTest(testId) {
    console.log('Start test:', testId);
}

function viewTest(testId) {
    console.log('View test:', testId);
}

function completeTest(testId) {
    console.log('Complete test:', testId);
}

function enterResults(testId) {
    document.getElementById('testId').value = testId;
    document.getElementById('testResultsModal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function submitTestResults(event) {
    event.preventDefault();
    console.log('Submit test results');
    closeModal('testResultsModal');
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}
