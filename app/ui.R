library(shiny)
library(plotly)
navbarPage(
    title = 'Mutual Fund Analysis',
    tabPanel('NAV',
        fluidPage(
            sidebarPanel(
                selectizeInput("mf_name", "Select Mutual Fund:", choices=c())
            ),
            mainPanel(
                DT::dataTableOutput('table_nav')
            )
        )
    ),
    tabPanel('CAGR',
        fluidPage(
            DT::dataTableOutput('table_cagr'),
            plotlyOutput('plot_density'),
            selectInput("year_hist", "Year:", choices=c(1:10)),
            plotlyOutput('plot_hist')
        )
    )

)