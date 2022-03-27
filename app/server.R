# source('../src/returns.R')
library(DT)
library(shiny)
library(rjson)
library(data.table)
library(ggplot2)
library(plotly)

mf_list_url <- 'https://api.mfapi.in/mf'
mf_list <- fromJSON(paste(readLines(mf_list_url), collapse=""))
dt_mfs <- data.table(do.call(rbind.data.frame, mf_list))

function(input, output, session) {
    updateSelectizeInput(session, "mf_name", choices = unique(dt_mfs$schemeName), server=TRUE)

    output$table1 <- DT::renderDataTable(
        datatable(cars, filter='top', options = list(pageLength = 25))
    )
    output$table2 <- DT::renderDataTable(
        datatable(mtcars, filter='top', options = list(pageLength = 25))
    )
    #output$plot1 <- renderPlotly({
    #    ggplotly(p)
    #})
}