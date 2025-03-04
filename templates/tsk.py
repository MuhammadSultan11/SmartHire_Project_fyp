

# Known values
current_cgpa = 2.92
current_earned_credits = 93
current_semester_gpa = 3.3
current_semester_credits = 17

# Calculate new CGPA
new_cgpa = ((current_cgpa * current_earned_credits) + 
            (current_semester_gpa * current_semester_credits)) / \
           (current_earned_credits + current_semester_credits)

print("current:",new_cgpa)
print("______________________")

# Known values
current_cgpa = new_cgpa
current_earned_credits = 93+17
current_semester_gpa = 3.3
current_semester_credits = 18

# Calculate new CGPA
new_cgpa = ((current_cgpa * current_earned_credits) + 
            (current_semester_gpa * current_semester_credits)) / \
           (current_earned_credits + current_semester_credits)

print("next:",new_cgpa)
print("______________________")

# Known values
current_cgpa = new_cgpa
current_earned_credits = 93+17+18+8
current_semester_gpa = 3.4
current_semester_credits = 8

# Calculate new CGPA
new_cgpa = ((current_cgpa * current_earned_credits) + 
            (current_semester_gpa * current_semester_credits)) / \
           (current_earned_credits + current_semester_credits)

print("up next:",new_cgpa)
print("______________________")




from sympy import symbols, Eq, solve

# Define variables
G1, G2, G3 = symbols('G1 G2 G3')

# Known values
target_cgpa = 3.0
next_credits = 18
up_next_credits = 8
current_earned_credits = 93
current_cgpa = 2.84
# Total credits after three semesters
total_credits = current_earned_credits +17 + next_credits + up_next_credits

# Equation for target CGPApi
cgpa_equation = Eq(
    (current_cgpa * current_earned_credits) + (G1 * 17) + (G2 * next_credits) + (G3 * up_next_credits),
    target_cgpa * total_credits
)

# Solving for G1 = G2 = G3
solution = solve(cgpa_equation.subs({G1: G2, G2: G3}), G3)
print(solution)
required_gpa = solution[0]
print(required_gpa)
