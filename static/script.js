// Draw the loans graph



// Convert "2016-01-23" to UTC date
function dateStringToUTC(s)
{
    var d = new Date(s);
    return Date.UTC(d.getYear() + 1900, d.getMonth(), d.getDate());
}

// Draw the graph
$(function() {

    if ( ! document.getElementById("loans_graph") )
        return;

    // Parse the data into an array of objects of format:
    // name: "series name"
    // data: [[x1, y1], [x2, y2], ...]
    var data = [];
    for ( var n in loans ) {        // each name
        var s = loans[n],           // list of [date, amt] pairs
            cumul = 0,              // cumulative value
            points = [];            // array of points to add
        for ( var i = 0; i < s.length; ++i ) {
            var x = s[i][0],        // date as string
                y = s[i][1] * 1;    // amount for this deposit
            cumul += y;             // convert to cumulative
            points.push([dateStringToUTC(x), cumul]);
        }
        data.push({ name: n, data: points });
    }

    // Draw the graph
    $("#loans_graph").highcharts({
        chart: { type: "line" },
        title: { text: null }, //"Loans to Datamind" },
        xAxis: { 
            type: "datetime", 
            title: { text: "Date" }
        },
        yAxis: { title: { text: "Cumulative" }, min: 0 },
        tooltip: {
            headerFormat: "<b>{series.name}</b><br>",
            pointFormat: "{point.x: %e %b}: {point.y: .2f}"
        },
        legend: {
            layout: "horizontal",
            align: "center",
            verticalAlign: "top",
            floating: true,
            borderWidth: 1,
            margin: 20
        },
        plotOptions: { spline: { marker: { enabled: true } } },
        series: data
    });
});


