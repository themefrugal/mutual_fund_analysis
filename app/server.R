source('../src/utils.R')
library(DT)
library(shiny)
library(rjson)
library(data.table)
library(ggplot2)
library(plotly)
library(dplyr)

# mf_list_url <- 'https://api.mfapi.in/mf'
# mf_list <- fromJSON(paste(readLines(mf_list_url), collapse=""))
# dt_mfs <- data.table(do.call(rbind.data.frame, mf_list))
# save(dt_mfs, file = 'mf_codes.RData')

load('./mf_codes.RData')

function(input, output, session) {
    updateSelectizeInput(session, "mf_name", choices = unique(dt_mfs$schemeName), server=TRUE)

    navs <- reactive({
        mf_url <- paste0('https://api.mfapi.in/mf/', dt_mfs[schemeName == input$mf_name]$schemeCode)
        dt_navs <- get_navs(mf_url)
        dt_navs
    })

    cagrs <- reactive({
        dt_cagrs <- rbindlist(lapply(c(1:10), function(x)get_cagr(navs(), x)))
    })

    output$table_nav <- DT::renderDataTable(
        datatable(navs(), filter='top', options = list(pageLength = 25)) %>%
            formatRound(columns=c('nav'), digits=3)
    )

    output$table_cagr <- DT::renderDataTable(
        datatable(cagrs(), filter='top', options = list(pageLength = 25)) %>%
            formatRound(columns=c('cagr', 'min', 'P25', 'mean', 'median', 'P75', 'max'), digits=3)
    )

    output$plot_density <- renderPlotly({
        p <- ggplot(cagrs(), aes(x=cagr, color=years)) + geom_density() +
            scale_color_brewer(palette="Dark2") + theme_minimal()
        ggplotly(p)
    })

    output$plot_hist <- renderPlotly({
        p <- ggplot(cagrs()[years == input$year_hist], aes(x=cagr)) +
            geom_histogram() +
            geom_vline(aes(xintercept = mean), colour="black") +
            geom_vline(aes(xintercept = median), colour="red") +
            geom_vline(aes(xintercept = min), colour="black") +
            geom_vline(aes(xintercept = max), colour="black") +
            geom_vline(aes(xintercept = P25), colour="blue") +
            geom_vline(aes(xintercept = P75), colour="blue")
        ggplotly(p)
    })

    output$plot_rolling <- renderPlotly({
        p <- ggplot(cagrs(), aes(x=date, y=cagr, color=years)) +
            geom_line()
        ggplotly(p)
    })

    # NAV Plot
    output$plot_nav <- renderPlotly({
        p <- ggplot(navs(), aes(x=date, y=nav)) + geom_line()
        if(input$nav_log_y){
            p <- p + scale_y_log10()
        }
        ggplotly(p)
    })

    # Cumulative Return Plot
    output$plot_cumr <- renderPlotly({
        dt_cumr <- get_cumulative_returns(navs(), input$start_date)
        p <- ggplot(dt_cumr, aes(x=date, y=cum_returns)) + geom_line() + scale_y_log10()
        ggplotly(p)
    })
}
# [years == input$year_rolling]