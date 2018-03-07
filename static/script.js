// Event handlers for accounts system.


// Event handler for clicking the checkbox on a transaction
function checkReconcile(evt)
{
    // Get the checkbox and its current status
    var cbox = evt.target;

    // Get the debit and credit values from the same row on the table
    var td = cbox.parentElement,                // the surrounding table cell
        drCell = td.nextSibling.nextSibling,    // next cell over (skip over newline)
        drAmt = drCell.firstChild,              // contents of the debit cell
        crCell = drCell.nextSibling.nextSibling,// next cell over (skip over newline)
        crAmt = crCell.firstChild;              // contents of the credit cell
    drAmt = drAmt ? parseFloat(drAmt.data) : 0; // the amount, 0 if blank
    crAmt = crAmt ? parseFloat(crAmt.data) : 0;

    // Calculate the net amount for the transaction, and update global variable
    // with total value of transactions cleared in this session
    var netAmt = drAmt - crAmt;
    if ( cbox.checked )
        cleared += netAmt;
    else
        cleared -= netAmt;

    // Update three fields in the reconciliation box: cleared, total cleared,
    // and difference
    gid("cleared").firstChild.data = cleared;
    gid("tot_cleared").firstChild.data = pr_cleared + cleared;
    gid("diff").firstChild.data = stmt_bal - (pr_cleared + cleared);

    // Enable/disable the "done" button, enable only if difference is zero

    // Send an AJAX request to the server, to toggle the cleared column for
    // this transaction
    var http = getHttp();
    http.onreadystatechange = function() {
        if ( http.readyState == 4 ) {
            console.log(http.responseText);
        };
    };
    http.open('POST', 'reconcileEvent', true);
    http.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    http.send(cbox.id + '=' + cbox.checked);
}


// Update the statement balance during reconciliation
function reconcileSetStmtBal(evt)
{
    // Get field value, make sure a number
    var field = evt.target,
        value = parseFloat(field.value);
    if ( isNaN(value) ) {
        alert("Invalid value!");
        return;
    }

    // Update the value in global variable
    stmt_bal = value;

    // Update the "difference" field
    gid("diff").firstChild.data = stmt_bal - (pr_cleared + cleared);

    // Send an AJAX request to the server, to update the value
    var http = getHttp();
    http.onreadystatechange = function() {
        if ( http.readyState == 4 ) {
            console.log(http.responseText);
        };
    };
    http.open('POST', 'reconcileEvent', true);
    http.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    http.send('stmtbal=' + stmt_bal);
}


// Get element by id
function gid(eid)
{
    return document.getElementById(eid);
}


// Convert "2016-01-23" to UTC date, for highcharts time axis
function dateStringToUTC(s)
{
    var d = new Date(s);
    return Date.UTC(d.getYear() + 1900, d.getMonth(), d.getDate());
}


// Get the AJAX request object
function getHttp()
{
    var h = null;
    if ( window.ActiveXObject ) {
        try {
            h = new window.ActiveXObject("Microsoft.XMLHTTP");
        } catch ( e ) {
            h = null;
        }
    }
    else
        h = new XMLHttpRequest();
    if ( ! h ) 
        console.log("Could not contact server");
    return h;
}

