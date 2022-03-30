source('../src/utils.R')
library(DT)
library(shiny)
library(rjson)
library(data.table)
library(ggplot2)
library(plotly)

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
        datatable(navs(), filter='top', options = list(pageLength = 25))
    )

    output$table_cagr <- DT::renderDataTable(
        datatable(cagrs(), filter='top', options = list(pageLength = 25))
    )

    output$plot1 <- renderPlotly({
        p <- ggplot(cagrs(), aes(x=cagr, color=years)) + geom_density() +
            scale_color_brewer(palette="Dark2") + theme_minimal()
        ggplotly(p)
    })
}