source('../src/returns.R')
library(DT)
library(shiny)

function(input, output) {
    output$table1 <- DT::renderDataTable(
        datatable(dt_navs, filter='top', options = list(pageLength = 25))
    )
    output$table2 <- DT::renderDataTable(
        datatable(dt_cagrs, filter='top', options = list(pageLength = 25))
    )
    output$plot1 <- renderPlotly({
        ggplotly(p)
    })
}