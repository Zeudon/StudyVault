1. Frontend 
-  Create a frontend application using React and TypeScript, with all the necessary libraries to do the below.
- Create a landing page with Sign In or Sign Up page. Make the Sign In/Sign Up a button on the top navigation bar, which upon being clicked will open a modal for signing in or sign up.
- If user clicks on Sign In, prompt user to enter email id and password, and authenticate the credentials by sending it to the backend and awaiting the response.
- If user clicks on Sign Up, prompt details such as First Name, Last Name, Email ID, Password, and upon clicking Submit, the details should be sent to the backend via an API call.
- The landing page should look modern and classy, with the name of the app - StudyVault, which is a personal tutor and library that allows users to upload PDFs and videos, and query their data using a chatbot to get answers quicker, learn better or to just refresh what they had seen before.
- Once user logs in, the top navigation bar should have 2 buttons - Library and Log Out. the default page is the Library page.
- The library page shows the contents uploaded by the user - this can be either PDFs or YouTube links. Users can choose to delete any particular content if they choose to.


2. Backend
- Create a FastAPI backend in the backend folder.
- The backend should support APIs to authenticate user login, another API to store user credentials when they sign in, an API to retrieve a user's library contents.
- It should also expose an API to upload a new PDF or a YouTube link.
- Another API to delete an existing item (PDF or YouTube link)
- An integration with LangChain to index the data and store in a vector DB such as Qdrant.
- Integrate with a PostgreSQL db to store user details, another table to store user library data.



