library(shiny)
navbarPage(
    title = 'Mutual Fund Analysis',
    tabPanel('Tab 1',
        fluidPage(
            sidebarPanel(
                selectizeInput("mf_name", "Select Mutual Fund:", choices=c())
            ),
            mainPanel(
                DT::dataTableOutput('table1')
                # plotlyOutput('plot1')
            )
        )
    ),
    tabPanel('Tab 2',
        fluidPage(
            DT::dataTableOutput('table2')
        )
    )

)