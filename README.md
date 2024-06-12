# Budgie Financial Dashboard

_A quick visualizer to monitor your personal finances._

Process your bank transactions to get an overview of your spending, categorize transactions, and define budget areas.

![app screenshot](/src/assets/screenshot.PNG)


# Getting Started
There are two ways to use Budgie:
1. [Download the executable file](https://1drv.ms/f/s!AmMd5hpZTnZ3hZEyNDFWxb45dM2M5Q?e=wP6Yvv) to run from your command line
2. Clone the source code and run in your local Python environment

There are also two ways to store your financial data:
1. A set of CSV files
2. A Mongo database

Budgie is built on the default CSV transactions that come from your bank. The CSV files are uploaded to Budgie and 
separated by account.

Add a new account by selecting the "Add New Account..." option from the accounts drop down menu.
Type the account name and instantiate that account by selecting a transaction CSV file from your financial institution to upload. 
Once the account is logged in your database, you can upload more transactions CSV files under that account. 
You can select multiple files to upload simultaneously for the same account.

You can also manually input transactions with the "Add Manual Transaction" menu.

After the transactions are loaded, you can update their details in the "Transactions" tab either by double-clicking on the data or by selecting one or multiple rows
and updating with the "Edit" button.

Budgie will attempt to auto-categorize new transactions based on previous transactions with a similar description. 

Once you categorize the transactions, you can add a budget and see your current status for different categories in the "Budget" tab
and use the filters on the Configurations sidebar to look for trends in your finances.



## Running Budgie

### Use the Executable
Download the [newest version of Budgie](https://1drv.ms/f/s!AmMd5hpZTnZ3hZEyNDFWxb45dM2M5Q?e=wP6Yvv). When you launch it, it will open a command window with logging information.

Open a web browser and go to http://127.0.0.1:8050/ to access the app. 


### Clone the Source Code

Clone the repository to your computer. Make a python environment and install the required libraries.

Start the Dash app with `python app()` and then access the app at http://127.0.0.1:8050/.

## Storing Data
### CSV File
If you are using the executable version of the program, a new folder called `data` will be created to store the files in the same location as the executable.

Alternatively, you can specify a path with an `.env` file in the same directory as the executable, or at the top level of the repository, which contains:
    
    DATA_DIR=C:\path\to\data\directory

When you add new transactions or update your budget, Budgie will automatically rewrite the CSV with the new data. 
You can also click the "Export Data" button on bottom left of the Budgie app to manually export your data.


### Mongo Database
Instantiate a Mongo database and store the information in a `.env` file in the top level of this repository following the template:
    
    MONGO_HOST=mongodb://127.0.0.0:27017/
    MONGO_DB=your_database_name
    BACKUP_DIR=directory to save backup files [optional]

Start the Dash app with `python app()` and then access the app at http://127.0.0.1:8050/.

You can export the database data as CSV files by clicking the "Export Data" button on bottom left of the Budgie app to manually export your data to the specified `BACKUP_DIR` 
location or the default location, the root directory of the repository.



## Getting Started with Python and MongoDB

#### Getting Python 
My preference of IDE and package manager is [PyCharm Community](https://www.jetbrains.com/pycharm/download/?section=windows) 
and [Miniconda](https://docs.anaconda.com/free/miniconda/).

* Once you install Miniconda, you can create a new environment with `conda creat --name env_name python=3.10`
* Install all the required packages by first activating the environment with `conda activate env_name`
* Navigate to the Budgie source directory and run `pip install -r requirements.txt`
* Add `env_name` as the 

#### Installing MongoDB on Windows
1. Download the [MongoDB installer](https://www.mongodb.com/try/download/community) and the [Mongo Shell](https://www.mongodb.com/try/download/shell). You'll only want to install it as a service if you want your database to automatically when your computer turns on. 
    
    Unzip the Mongo Shell file and copy `mongo.sh` into

2. Now update your environment variable for Mongo. Access it through

    `Control Panel > System & Security > System > Advanced System Settings > Environment Variables`

    Edit the `Path` User Variable by adding a new variable of the path to your MongoDB bin file (making sure it ends with a `\ `),
    so it should be along the lines of: `C:\Program Files\MongoDB\Server\7.0\bin\ `
    
3. Create a new directory for your data `C:\data\db`

4. In a command prompt, run the command `mongod` to start the database

5. In a second command prompt, run the command `mongosh` to start the database shell. Here, you can manipulate the database if you're a command line warrior. Also, 
don't worry about closing the command prompts when you're done, Mongo saves all the data.

6. Now, you can run `app.py` or the executable file and start using Budgie by uploading a transaction CSV file to a new account


## Security
All transaction data is stored locally on your machine as CSV files or on your MongoDB instance. 

Please ensure you do not push any personal information into the repository.


## Troubleshooting

### CSV file upload fails
If your financial institution's CSV fails to be uploaded, make an issue that includes the header of the CSV and a line of a representative credit (+) and debit (-) to the account.

### Special note about Venmo
Venmo allows you to spend either from your Venmo account balance, or from a third party account. To denote when these transactions are from an alternative source, it should be marked in the 
transaction notes as "Source: [source information]" in order to properly calculate your net worth. 

### Slow performance
I've only run the CSV file option with a couple thousand transactions (for me, about a handful of years worth transactions). Substantially larger amounts of data may experience slower performance,
and if so, please make an issue for it so I can address that.