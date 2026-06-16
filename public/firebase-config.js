// Firebase configuration for AutoFinance
// This file is used by the frontend to connect to Firebase

const firebaseConfig = {
  apiKey: "AIzaSyAhMCSOfsBZLDOn5tzOZnOnPNttqKS5Am0",
  authDomain: "autofinance-ing.firebaseapp.com",
  projectId: "autofinance-ing",
  storageBucket: "autofinance-ing.firebasestorage.app",
  messagingSenderId: "10355149732",
  appId: "1:10355149732:web:596405d4f503bedff98f31"
};

// Initialize Firebase
if (typeof firebase !== 'undefined') {
  firebase.initializeApp(firebaseConfig);
  console.log("Firebase initialized successfully!");
} else {
  console.error("Firebase library not loaded");
}
