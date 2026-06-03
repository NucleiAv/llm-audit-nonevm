use anchor_lang::prelude::*;

declare_id!("BUMPV3111111111111111111111111111111111111");

#[program]
pub mod escrow {
    use super::*;

    pub fn initialize_escrow(ctx: Context<InitEscrow>, amount: u64) -> Result<()> {
        let escrow = &mut ctx.accounts.escrow;
        escrow.bump = *ctx.bumps.get("escrow").unwrap();
        escrow.depositor = ctx.accounts.depositor.key();
        escrow.amount = amount;
        Ok(())
    }

    pub fn release_escrow(ctx: Context<ReleaseEscrow>) -> Result<()> {
        Ok(())
    }
}

#[derive(Accounts)]
pub struct InitEscrow<'info> {
    #[account(
        init,
        payer = depositor,
        space = 8 + Escrow::SIZE,
        seeds = [b"escrow", depositor.key().as_ref()],
        bump
    )]
    pub escrow: Account<'info, Escrow>,
    #[account(mut)]
    pub depositor: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ReleaseEscrow<'info> {
    #[account(
        mut,
        seeds = [b"escrow", depositor.key().as_ref()],
        bump = escrow.bump,
        has_one = depositor
    )]
    pub escrow: Account<'info, Escrow>,
    pub depositor: Signer<'info>,
}

#[account]
pub struct Escrow {
    pub depositor: Pubkey,
    pub amount: u64,
    pub bump: u8,
}

impl Escrow {
    pub const SIZE: usize = 32 + 8 + 1;
}
