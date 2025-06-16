# chatbot/logic.py

def get_diagnosis(symptoms):
    symptoms = symptoms.lower()

    if "fever" in symptoms and "cough" in symptoms:
        return (
            "Possible Flu",
            "Take rest, drink plenty of fluids, and consult a physician if symptoms persist.",
            [
                {"name": "Dr. Priya Sharma", "address": "Apollo Clinic, Koramangala, Bangalore"},
                {"name": "Dr. Ramesh Rao", "address": "Manipal Hospital, Old Airport Road, Bangalore"}
            ]
        )
    elif "headache" in symptoms and "nausea" in symptoms:
        return (
            "Possible Migraine",
            "Avoid screen time, rest in a dark room, and consult a neurologist.",
            [
                {"name": "Dr. Kavitha S", "address": "Fortis Hospital, Bannerghatta Road, Bangalore"},
                {"name": "Dr. Arun Raj", "address": "Sakra World Hospital, Marathahalli, Bangalore"}
            ]
        )
    elif "sore throat" in symptoms or "sneezing" in symptoms:
        return (
            "Possible Common Cold",
            "Drink warm fluids, rest well, and consider steam inhalation.",
            [
                {"name": "Dr. Meenakshi", "address": "Cloudnine Clinic, Jayanagar, Bangalore"},
                {"name": "Dr. Sanjay Patil", "address": "Columbia Asia Hospital, Hebbal, Bangalore"}
            ]
        )
    else:
        return (
            "Unknown condition",
            "Sorry, we couldn't identify the condition. Please consult a healthcare professional.",
            []
        )
        # Test the function manually
if __name__ == "__main__":
    user_input = input("Enter your symptoms: ")
    diagnosis, solution, doctors = get_diagnosis(user_input)

    print(f"\nDiagnosis: {diagnosis}")
    print(f"Solution: {solution}")
    if doctors:
        print("\nRecommended Doctors in Bangalore:")
        for doc in doctors:
            print(f"- {doc['name']}, {doc['address']}")